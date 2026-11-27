"""Read-only live browser acceptance smoke for the Opera+ Atlas ecosystem.

No publication, test emails, or credentials. Check the deployed pages rather
than a local fixture; transient failures remain non-conclusive and get one retry.
"""
import asyncio
import json
import re
import tempfile
from pathlib import Path

from scripts.audit_public_atlas import read_targets, scan

ATLAS="https://opera.plus/atlas/"
OBS="https://opera.plus/osservatorio/"
EXPLORE=OBS+"esplora/"
DASH="https://jeckodevelopment.com/dev/atlas/"
VENUE_IDS={"oa-v-000064","oa-v-000074"}

def number(value):
    if not re.fullmatch(r"[\d.\s\u00a0\u202f]+",value.strip()):
        raise ValueError("non-numeric rendered metric: "+value)
    return int(re.sub(r"\D","",value))

async def open_page(page,url,ready):
    response=await page.goto(url,wait_until="domcontentloaded",timeout=30000)
    if response is None or response.status!=200:
        raise RuntimeError(f"unexpected HTTP response for {url}")
    await page.locator(ready).wait_for(state="visible",timeout=45000)

async def metrics(browser):
    context=await browser.new_context(locale="it-IT",accept_downloads=True)
    try:
        p=await context.new_page()
        await open_page(p,OBS,"#content")
        for name in ("year","season","region"):
            await p.locator("#"+name).select_option("all")
        obs={name:number(await p.locator("#k-"+key).inner_text())
             for name,key in (("Produzioni","stagings"),("Recite rilevate","perfs"),
                              ("Opere","works"),("Teatri e sedi","venues"))}
        for button,kind in (("#download","csv"),("#report-pdf","pdf")):
            async with p.expect_download(timeout=30000) as event:
                await p.locator(button).click()
            item=await event.value
            contents=Path(await item.path()).read_bytes()
            if not contents or (kind=="pdf" and not contents.startswith(b"%PDF-")):
                raise ValueError("invalid Observatory export: "+kind)
        await open_page(p,EXPLORE,"#explore-content")
        await p.locator("#reset").click()
        await p.locator("#metrics article").first.wait_for()
        exp={}
        for article in await p.locator("#metrics article").all():
            label=await article.locator("p").inner_text()
            exp[label]=number(await article.locator("strong").inner_text())
        if not all(obs[k]==exp.get(k) for k in obs) or not obs["Recite rilevate"]:
            raise AssertionError(f"live Observatory/Explore metrics differ: {obs} vs {exp}")
        for button,kind in (("#export-detail","csv"),("#export-pdf","pdf")):
            async with p.expect_download(timeout=30000) as event:
                await p.locator(button).click()
            item=await event.value
            contents=Path(await item.path()).read_bytes()
            if not contents or (kind=="pdf" and not contents.startswith(b"%PDF-")):
                raise ValueError("invalid Explore export: "+kind)
        return {"observatory":obs,"explore":exp,"exports":"csv_and_pdf"}
    finally:
        await context.close()

async def homepage(browser):
    context=await browser.new_context(locale="it-IT",viewport={"width":390,"height":844},is_mobile=True,has_touch=True)
    try:
        p=await context.new_page()
        await open_page(p,ATLAS,"#filters")
        await p.wait_for_function("() => document.querySelector('#count') && !document.querySelector('#count').textContent.includes('Caricamento')",timeout=45000)
        await p.locator("#radius").select_option("all")
        await p.locator("#period").select_option("all")
        await p.locator("#events a").first.wait_for(timeout=45000)
        nav=p.locator(".mobile-nav")
        await nav.wait_for(state="visible")
        links=await nav.locator("a").count()
        if links<5:
            raise AssertionError("mobile navigation missing links")
        return {"mobile_navigation_links":links,"catalog_loaded":True}
    finally:
        await context.close()

async def dashboard(browser):
    context=await browser.new_context(locale="it-IT")
    try:
        p=await context.new_page()
        await open_page(p,DASH,"#freshness")
        await p.wait_for_function("() => document.querySelector('#freshness').textContent.includes('Dati caricati')",timeout=60000)
        await p.locator('[data-tab="venues"]').click()
        await p.locator("#venue-filter option[value=persistent]").wait_for(state="attached")
        await p.locator("#venue-filter").select_option("persistent")
        await p.locator("#venue-filter").select_option("all")
        await p.locator("#venue-rows tr").first.wait_for()
        return {"freshness":await p.locator("#freshness").inner_text(),"persistent_filter":True}
    finally:
        await context.close()

async def main():
    from playwright.async_api import async_playwright
    report={}
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(headless=True)
        try:
            for key,fn in (("atlas_mobile",homepage),("observatory_explore",metrics),("dashboard",dashboard)):
                for attempt in range(2):
                    try:
                        report[key]={"status":"verified","details":await fn(browser)}
                        break
                    except Exception as exc:
                        report[key]={"status":"unverified","error":type(exc).__name__,"detail":str(exc)[:500]}
            targets,_=read_targets()
            for item in (x for x in targets if x["id"] in VENUE_IDS):
                result=await scan(browser,item,asyncio.Semaphore(1))
                if result["status"]=="unverified":
                    result=await scan(browser,item,asyncio.Semaphore(1))
                report[item["id"]]=result
        finally:
            await browser.close()
    Path("ecosystem-smoke.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if not VENUE_IDS.issubset(report) or any(x["status"] not in ("verified","verified_live") for x in report.values()):
        raise SystemExit("One or more deployed checks remain unverified")

if __name__=="__main__":
    asyncio.run(main())

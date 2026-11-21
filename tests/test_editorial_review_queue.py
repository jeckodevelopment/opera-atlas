"""Review queue is derived from published cards, never from guesses."""
import unittest

from scripts.editorial_review_queue import evaluate


def card(work_id, title, synopsis, history=None):
    return {"work_id":work_id,"title":title,"composer":"Giovanni Paisiello",
            "slug":"il-barbiere-di-siviglia","route_slug":"il-barbiere-di-siviglia-paisiello",
            "synopsis":synopsis,"history":history}


class EditorialReviewQueueTests(unittest.TestCase):
    def test_identity_only_card_is_prioritized(self):
        source={"schema_version":1,"works":[
            card("oa-w-010","Il barbiere di Siviglia",
                 "«Il barbiere di Siviglia» è un'opera di Giovanni Paisiello. "
                 "Consulta le rappresentazioni verificate in programma nei teatri italiani.")]}
        result=evaluate(source)
        self.assertEqual(result["count"],1)
        self.assertEqual(result["identity_only_count"],1)
        self.assertEqual(result["missing_history_count"],1)
        self.assertEqual(result["works"][0]["priority"],"high")
        self.assertEqual(result["works"][0]["work_id"],"oa-w-010")

    def test_real_synopsis_kept_out_of_queue_when_history_complete(self):
        history={"librettist":"Giuseppe Petrosellini","premiere_year":1782,
                 "premiere_venue":"Teatro Imperiale","premiere_city":"San Pietroburgo",
                 "sources":["https://example.org/verified-record"]}
        source={"schema_version":1,"works":[
            card("oa-w-011","Il barbiere di Siviglia",
                 "Una vicenda di travestimenti e intrighi amorosi vede Figaro impegnato a favorire due innamorati.",
                 history)]}
        self.assertEqual(evaluate(source)["works"],[])

    def test_missing_history_only_has_normal_priority(self):
        source={"schema_version":1,"works":[
            card("oa-w-012","Il barbiere di Siviglia",
                 "Figaro aiuta a superare gli ostacoli tra due innamorati.", None)]}
        queue=evaluate(source)["works"]
        self.assertEqual(queue[0]["priority"],"normal")
        self.assertEqual(queue[0]["reasons"],["historical_facts_missing"])

    def test_two_homonyms_keep_separate_ids(self):
        source={"schema_version":1,"works":[
            card("oa-w-010","Il barbiere di Siviglia",
                 "«Il barbiere di Siviglia» è un'opera di Giovanni Paisiello. "
                 "Consulta le rappresentazioni verificate in programma nei teatri italiani."),
            card("oa-w-013","Il barbiere di Siviglia",
                 "«Il barbiere di Siviglia» è un'opera di Gioachino Rossini. "
                 "Consulta le rappresentazioni verificate in programma nei teatri italiani.")]}
        self.assertEqual({x["work_id"] for x in evaluate(source)["works"]},
                         {"oa-w-010","oa-w-013"})

    def test_duplicate_identity_fails(self):
        c=card("oa-w-010","Il barbiere di Siviglia","Some documented plot.")
        with self.assertRaises(ValueError):
            evaluate({"schema_version":1,"works":[c,c]})


if __name__=="__main__":
    unittest.main()

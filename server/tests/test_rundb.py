import datetime
import unittest

import util
from pymongo import DESCENDING

run_id = None


class CreateRunDBTest(unittest.TestCase):
    def setUp(self):
        self.rundb = util.get_rundb()
        self.rundb.runs.create_index(
            [("last_updated", DESCENDING), ("tc_base", DESCENDING)],
            name="finished_ltc_runs",
            partialFilterExpression={"finished": True, "tc_base": {"$gte": 40}},
        )

    def tearDown(self):
        self.rundb.runs.delete_many({"args.username": "travis"})
        # Shutdown flush thread:
        self.rundb.stop()

    def test_10_create_run(self):
        global run_id
        # STC
        run_id_stc = self.rundb.new_run(
            "master",
            "master",
            100000,
            "10+0.01",
            "10+0.01",
            "book",
            10,
            1,
            "",
            "",
            username="travis",
            tests_repo="travis",
            start_time=datetime.datetime.utcnow(),
        )
        run = self.rundb.get_run(run_id_stc)
        run["finished"] = True
        task = {
            "num_games": self.rundb.chunk_size,
            "stats": {"wins": 0, "draws": 0, "losses": 0, "crashes": 0},
            "pending": True,
            "active": True,
        }
        run["tasks"].append(task)

        self.rundb.buffer(run, True)

        # LTC
        run_id = self.rundb.new_run(
            "master",
            "master",
            100000,
            "150+0.01",
            "150+0.01",
            "book",
            10,
            1,
            "",
            "",
            username="travis",
            tests_repo="travis",
            start_time=datetime.datetime.utcnow(),
        )
        print(" ")
        print(run_id)
        run = self.rundb.get_run(run_id)
        task = {
            "num_games": self.rundb.chunk_size,
            "stats": {"wins": 0, "draws": 0, "losses": 0, "crashes": 0},
            "pending": True,
            "active": True,
        }
        run["tasks"].append(task)

        print(run["tasks"][0])
        self.assertTrue(run["tasks"][0][u"active"])
        run["tasks"][0][u"active"] = True
        run["tasks"][0][u"worker_info"] = {
            "username": "worker1",
            "unique_key": "travis",
            "concurrency": 1,
        }
        run["cores"] = 1

        for run in self.rundb.get_unfinished_runs():
            if run["args"]["username"] == "travis":
                print(run["args"])

    def test_20_update_task(self):
        run = self.rundb.get_run(run_id)
        run["tasks"][0][u"active"] = True
        run["tasks"][0][u"worker_info"] = {
            "username": "worker1",
            "unique_key": "travis",
            "concurrency": 1,
        }
        run["cores"] = 1
        self.rundb.buffer(run, True)
        run = self.rundb.update_task(
            run_id,
            0,
            {
                "wins": 1,
                "losses": 1,
                "draws": self.rundb.chunk_size - 3,
                "crashes": 0,
                "time_losses": 0,
            },
            1000000,
            "?",
            "",
            "worker2",
            "travis",
        )
        self.assertFalse(run["task_alive"])
        self.assertTrue("error" in run)
        run = self.rundb.update_task(
            run_id,
            0,
            {
                "wins": 1,
                "losses": 1,
                "draws": self.rundb.chunk_size - 4,
                "crashes": 0,
                "time_losses": 0,
            },
            1000000,
            "?",
            "",
            "worker1",
            "travis2",
        )
        self.assertFalse(run["task_alive"])
        self.assertTrue("info" in run)
        # revive task
        run_ = self.rundb.get_run(run_id)
        run_["tasks"][0]["active"] = True
        self.rundb.buffer(run_, True)
        run = self.rundb.update_task(
            run_id,
            0,
            {
                "wins": 1,
                "losses": 1,
                "draws": self.rundb.chunk_size - 4,
                "crashes": 0,
                "time_losses": 0,
            },
            1000000,
            "?",
            "",
            "worker1",
            "travis",
        )
        self.assertEqual(run, {"task_alive": True})
        run = self.rundb.update_task(
            run_id,
            0,
            {
                "wins": 1,
                "losses": 1,
                "draws": self.rundb.chunk_size - 2,
                "crashes": 0,
                "time_losses": 0,
            },
            1000000,
            "?",
            "",
            "worker1",
            "travis",
        )
        self.assertEqual(run, {"task_alive": False})

    def test_30_finish(self):
        print("run_id: {}".format(run_id))
        run = self.rundb.get_run(run_id)
        run["finished"] = True
        self.rundb.buffer(run, True)

    def test_40_list_LTC(self):
        finished_runs = self.rundb.get_finished_runs(limit=3, ltc_only=True)[0]
        for run in finished_runs:
            print(run["args"]["tc"])

    def test_90_delete_runs(self):
        for run in self.rundb.runs.find():
            if run["args"]["username"] == "travis" and "deleted" not in run:
                print("del ")
                run["deleted"] = True
                run["finished"] = True
                for w in run["tasks"]:
                    w["pending"] = False
                self.rundb.buffer(run, True)


if __name__ == "__main__":
    unittest.main()

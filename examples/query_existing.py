"""Read-only query of a pre-existing Seedance task owned by your Key."""

import argparse

from seedance_crewai import SeedanceRetrieveTaskTool

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("task_id")
a = p.parse_args()
print(SeedanceRetrieveTaskTool().run(task_id=a.task_id, wait_seconds=0))

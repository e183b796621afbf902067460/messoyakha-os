from dagster import JobDefinition
from that_depends import Provide

from messoyakha_test_strategy.containers.test_strategy import Container


@Container.inject
def main(job: JobDefinition = Provide[Container.job]) -> None:
    job.execute_in_process()


if __name__ == "__main__":
    main()

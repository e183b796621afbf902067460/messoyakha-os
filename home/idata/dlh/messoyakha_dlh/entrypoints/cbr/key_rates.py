from dagster import JobDefinition
from that_depends import Provide

from messoyakha_dlh.containers.cbr.key_rates import Container


@Container.inject
def main(job: JobDefinition = Provide[Container.job]) -> None:
    job.execute_in_process()


if __name__ == "__main__":
    main()

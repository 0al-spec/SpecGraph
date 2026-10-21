"""Read native execution identity once and project existing report shapes."""

from collections.abc import Mapping
from dataclasses import asdict, dataclass

from .context import ExecutionIdentity


@dataclass(frozen=True)
class PublicationExecutionContext:
    identity: ExecutionIdentity
    environment: str
    source_revision: str

    @classmethod
    def from_environment(cls, values: Mapping[str, str]) -> "PublicationExecutionContext":
        run_id = values.get("GITHUB_RUN_ID", "")
        repository = values.get("GITHUB_REPOSITORY", "0al-spec/SpecGraph")
        server = values.get("GITHUB_SERVER_URL", "https://github.com")
        return cls(
            identity=ExecutionIdentity(
                provider="github_actions" if run_id else "local",
                run_id=run_id,
                run_attempt=values.get("GITHUB_RUN_ATTEMPT", ""),
                uri=f"{server}/{repository}/actions/runs/{run_id}" if run_id else "local-run",
            ),
            environment="ci" if run_id else "local",
            source_revision=values.get("GITHUB_SHA", ""),
        )

    def provenance(self) -> dict[str, str]:
        return asdict(self.identity)

    def observation(self) -> dict[str, str]:
        return {
            **self.provenance(),
            "environment": self.environment,
            "source_revision": self.source_revision,
        }

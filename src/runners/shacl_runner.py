from .runner import Runner
from .commands import mk_command_shacl


class SHACLRunner(Runner):
    engine = "shacl"

    def mk_command(self, data_filename: str, output_filename: str) -> list[str]:
        """The command that validates `data_filename` (data, shapes and
        target declarations in one file). Engines that write the report to a
        file write it to `output_filename`, the others print it to stdout."""
        return mk_command_shacl(self.command_pattern, data_filename, output_filename)

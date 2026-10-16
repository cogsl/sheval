from .runner import Runner
from .commands import mk_command_shex


class ShExRunner(Runner):
    engine = "shex"

    def mk_command(self, data_filename: str, shex_filename: str, shapemap_filename: str, output_filename: str) -> list[str]:
        """The command that validates the shapemap. Engines that write the
        result to a file write it to `output_filename`, the others print it
        to stdout."""
        return mk_command_shex(self.command_pattern, data_filename, shex_filename, shapemap_filename, output_filename)

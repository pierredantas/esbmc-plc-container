"""Convert a PLCopen XML program to Structured Text using Beremiz's own generator."""
import sys, os
BER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "beremiz")
sys.path.insert(0, BER)
os.chdir(BER)

# Beremiz pulls wx in only for its translation catalogue; the generator itself is
# GUI-free, so a stub is enough to run it headless.
import types                                       # noqa: E402
_wx = types.ModuleType("wx")
_wx.GetTranslation = lambda s: s
_wx.SetDefaultPyEncoding = lambda *a, **k: None
_wx.GetApp = lambda: None
sys.modules.setdefault("wx", _wx)

from plcopen.plcopen import LoadProject          # noqa: E402
from PLCGenerator import GenerateCurrentProgram  # noqa: E402


from plcopen.structures import StdBlckDct              # noqa: E402


class StubControler:
    """The few controller methods PLCGenerator reaches for.

    Block types come from Beremiz's own standard block dictionary rather than a
    hand-written table, so AND, OR, TON and the rest resolve exactly as they do
    inside the IDE.
    """
    def GetBaseType(self, name):
        return name

    def GetConfigurationExtraVariables(self):
        return []

    def __init__(self, project=None):
        self.project = project

    def GetProject(self, debug=False):
        return self.project

    def GetBlockType(self, typename, inputs=None, debug=False):
        entries = StdBlckDct.get(typename, [])
        if not entries:
            # a POU defined in this project, the way PLCControler falls back
            pou = self.project.getpou(typename) if self.project is not None else None
            return pou.getblockInfos() if pou is not None else None
        blocktype = entries[0][1].copy()
        if inputs not in (None, "undefined") and len(inputs) > len(blocktype["inputs"]):
            # AND, OR and friends are variadic; widen the signature to the call.
            first = blocktype["inputs"][0]
            blocktype["inputs"] = [(f"IN{i + 1}", first[1], first[2])
                                   for i in range(len(inputs))]
        return blocktype

    def GetPouType(self, name, debug=False):
        return None

    def IsOfType(self, type_name, reference, debug=False):
        return reference in ("ANY", type_name)


def main(path):
    project, error = LoadProject(path)
    if error is not None:
        print("LOAD ERROR:", error)
        return 2
    errors, warnings = [], []
    program = GenerateCurrentProgram(StubControler(project), project, errors, warnings)
    if errors:
        print("GENERATE ERRORS:", errors)
        return 3
    for w in warnings:
        print("warning:", w)
    # the generator returns [(text, refs), ...]
    text = program if isinstance(program, str) else "".join(
        chunk[0] if isinstance(chunk, tuple) else str(chunk) for chunk in program)
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(os.path.abspath(sys.argv[1])))

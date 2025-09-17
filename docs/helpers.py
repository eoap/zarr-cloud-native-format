import graphviz
from cwl2puml import to_puml, DiagramType
from cwltool.main import main as cwlmain
from cwltool.context import LoadingContext, RuntimeContext
from cwltool.executors import NoopJobExecutor
from io import StringIO, BytesIO
from IPython.display import Markdown, display
from eoap_cwlwrap import _search_workflow
from eoap_cwlwrap.types import type_to_string
from cwl_loader import load_cwl_from_location
from PIL import Image
from plantuml import deflate_and_encode
from urllib.request import urlopen


class WorkflowViewer:
    def __init__(self, cwl_file, workflow, entrypoint):
        self.cwl_file = cwl_file
        self.workflow = workflow
        self.entrypoint = entrypoint
        self.output = ".wrapped.cwl"
        self.base_url = "https://raw.githubusercontent.com/eoap/application-package-patterns/refs/heads/main"

    @staticmethod
    def from_file(cwl_file, entrypoint):
        workflow = load_cwl_from_location(path=cwl_file)
        return WorkflowViewer(cwl_file, workflow, entrypoint)

    @staticmethod
    def from_reference(cwl_file, workflow, entrypoint):
        return WorkflowViewer(cwl_file, workflow, entrypoint)

    def _prepare_headers(self, headers: list[str]):
        return f"| {' | '.join(headers)} |\n| {' | '.join(["---"] * len(headers))} |\n"

    def _display_parameters(self, parameters_name, entrypoint=None):
        md = self._prepare_headers(["Id", "Type", "Label", "Doc"])

        if entrypoint is None:
            entrypoint = self.entrypoint

        wf = _search_workflow(workflow_id=entrypoint, workflow=self.workflow)

        for p in getattr(wf, parameters_name, []):
            md += f"| `{p.id}` | `{type_to_string(p.type_)}` | {p.label} | {p.doc} |\n"

        display(Markdown(md))

    def display_inputs(self, entrypoint=None):
        self._display_parameters("inputs", entrypoint=entrypoint)

    def display_outputs(self, entrypoint=None):
        self._display_parameters("outputs", entrypoint=entrypoint)

    def display_steps(self):
        md = self._prepare_headers(["Id", "Runs", "Label", "Doc"])

        for step in _search_workflow(
            workflow_id=self.entrypoint, workflow=self.workflow
        ).steps:
            md += f"| `{step.id.replace(f'file:///#{self.entrypoint}/', '')}` | `{step.run}` | {step.label} | {step.doc} |\n"

        display(Markdown(md))

    def _display_puml(self, diagram_type: DiagramType, wf):

        out = StringIO()
        to_puml(
            cwl_document=wf,
            diagram_type=diagram_type,
            output_stream=out,
        )

        clear_output = out.getvalue()
        encoded = deflate_and_encode(clear_output)

        diagram_url = f"https://img.plantuml.biz/plantuml/png/{encoded}"

        with urlopen(diagram_url) as url:
            img = Image.open(BytesIO(url.read()))
        display(img)

    def display_components_diagram(self, entrypoint=None):
        
        if entrypoint is not None: 
            wf = _search_workflow(workflow_id=entrypoint, workflow=self.workflow)
        else:
            wf = self.workflow

        self._display_puml(DiagramType.COMPONENTS, wf=wf)

    def display_class_diagram(self, entrypoint=None):
        if entrypoint is None:
            entrypoint = self.entrypoint

        wf = _search_workflow(workflow_id=entrypoint, workflow=self.workflow)
        self._display_puml(DiagramType.CLASS, wf=wf)

    def plot(self):
        args = ["--print-dot", f"{self.cwl_file}#{self.entrypoint}"]

        stream_err = StringIO()
        stream_out = StringIO()

        _ = cwlmain(
            args,
            stdout=stream_out,
            stderr=stream_err,
            executor=NoopJobExecutor(),
            loadingContext=LoadingContext(),
            runtimeContext=RuntimeContext(),
        )

        return graphviz.Source(stream_out.getvalue())

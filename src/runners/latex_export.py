"""
Render sheval results as a LaTeX table, mirroring Table 2 of the
"Common Foundations for Recursive Shape Languages" paper: one row per test,
one column per (engine, technology), plus GFP/LFP/bSMS/cSMS columns showing
the verdict prescribed by each semantics (independent of any engine run).

Technology columns follow the order declared by the manifest's
shex_technologies/shacl_technologies lists.

The concrete LaTeX for each mark (pass/fail/error/na) and for each technology
name comes from a macros config file (see config/latex_macros.yaml), not from
this module, so the visual style and displayed names can be changed without
touching code.
"""

import yaml

from .error_type import ErrorType

_LATEX_SPECIAL_CHARS = {
    '\\': r'\textbackslash{}',
    '&': r'\&',
    '%': r'\%',
    '$': r'\$',
    '#': r'\#',
    '_': r'\_',
    '{': r'\{',
    '}': r'\}',
    '~': r'\textasciitilde{}',
    '^': r'\textasciicircum{}',
}

_ENGINE_SUFFIXES = ('_shex', '_shacl')

# Maps each ErrorType's value (as stored in result['error_type']) to the macro
# category it renders as. A result with an unrecognized/missing error_type
# (e.g. the generic "Error running command" fallback in error_classification)
# falls back to the generic 'error' category.
_ERROR_TYPE_CATEGORIES = {
    ErrorType.CYCLES_DETECTED.value: 'cycles_detected_stopped',
    ErrorType.NON_STRATIFIED.value: 'non_stratified_stopped',
    ErrorType.TIMEOUT.value: 'timeout',
    ErrorType.CRASHED.value: 'crashed',
    ErrorType.CYCLES_DETECTED_CRASHED.value: 'cycles_detected_crashed',
    ErrorType.NON_STRATIFIED_CRASHED.value: 'non_stratified_crashed',
    ErrorType.CYCLES_DETECTED_CONFORMANT.value: 'cycles_detected_conformant',
    ErrorType.CYCLES_DETECTED_NON_CONFORMANT.value: 'cycles_detected_non_conformant',
}

# error_type values whose result still carries a real conforms True/False (the
# engine warned but produced a usable report), so _engine_mark must check
# error_type before falling back to the plain pass/fail reading of conforms.
_CATEGORIES_OVERRIDING_CONFORMS = (
    ErrorType.CYCLES_DETECTED_CONFORMANT.value,
    ErrorType.CYCLES_DETECTED_NON_CONFORMANT.value,
)

_REQUIRED_MACRO_CATEGORIES = ('pass', 'fail', 'na', 'error') + tuple(_ERROR_TYPE_CATEGORIES.values())


def escape_latex(text):
    return ''.join(_LATEX_SPECIAL_CHARS.get(ch, ch) for ch in str(text))


def base_test_name(name):
    """Strip a trailing _shex/_shacl suffix so both engine variants of a test share one table row."""
    for suffix in _ENGINE_SUFFIXES:
        if name.endswith(suffix):
            return name[:-len(suffix)]
    return name


def load_latex_config(path):
    with open(path, 'r') as file:
        config = yaml.safe_load(file) or {}
    macros = config.get('macros', {})
    for category in _REQUIRED_MACRO_CATEGORIES:
        if category not in macros:
            raise ValueError(f"LaTeX macros config {path} is missing a '{category}' macro")
    return config


def _tech_columns(shex_technologies, shacl_technologies):
    """Ordered (engine, technology_name, suffix) columns, following the order the manifest
    declares its shex_technologies/shacl_technologies in. Disambiguates a technology name
    shared by both engines (e.g. rudof) with a '(ShEx)'/'(SHACL)' suffix."""
    shex_names = set(shex_technologies)
    shacl_names = set(shacl_technologies)
    columns = []
    for technology in shex_technologies:
        suffix = " (ShEx)" if technology in shacl_names else ""
        columns.append(('shex', technology, suffix))
    for technology in shacl_technologies:
        suffix = " (SHACL)" if technology in shex_names else ""
        columns.append(('shacl', technology, suffix))
    return columns


def _ordered_base_names(manifest_tests):
    seen = []
    for test in manifest_tests:
        name = base_test_name(test['name'])
        if name not in seen:
            seen.append(name)
    return seen


def _model_accepts(model):
    """A model accepts the schema if every declared pair is expected to pass under it."""
    return len(model.get('failing', [])) == 0


def _semantics_accepts(semantics_entry):
    """
    The verdict prescribed by one semantics entry, independent of any engine:
    True/False if it declares models, None if it's a 'conforms'-only entry
    (no fixed-point semantics applies, e.g. non-stratified catalogues).
    """
    models = semantics_entry.get('models')
    if models is None:
        return None
    quantifier = semantics_entry.get('quantifier', 'any')
    if quantifier == 'all':
        return all(_model_accepts(model) for model in models)
    return any(_model_accepts(model) for model in models)


def prescribed_marks(expected_results):
    """The GFP/LFP/bSMS/cSMS category ('pass'/'fail'/'na') prescribed by a test's expected_results, regardless of engine."""
    def mark_for(key):
        entry = expected_results.get(key)
        if entry is None:
            return 'na'
        accepts = _semantics_accepts(entry)
        if accepts is None:
            return 'na'
        return 'pass' if accepts else 'fail'
    return {
        'GFP': mark_for('gfp'),
        'LFP': mark_for('lfp'),
        'bSMS': mark_for('brave'),
        'cSMS': mark_for('cautious'),
    }


def _engine_mark(result):
    """result is None when the technology has no entry at all for this test
    (not applicable). A present result dict whose 'conforms' is neither True
    nor False means the run failed one way or another; the specific macro
    category is picked from its error_type, falling back to the generic
    'error' category when error_type is missing or unrecognized."""
    if result is None:
        return 'na'
    error_type = result.get('error_type')
    if error_type in _CATEGORIES_OVERRIDING_CONFORMS:
        return _ERROR_TYPE_CATEGORIES[error_type]
    conforms = result.get('conforms')
    if conforms is True:
        return 'pass'
    if conforms is False:
        return 'fail'
    return _ERROR_TYPE_CATEGORIES.get(error_type, 'error')


def build_latex_table(results, manifest, config):
    macros = config['macros']
    tech_macros = config.get('technologies', {})

    def macro(category):
        return "\\" + macros[category]['name']

    def tech_macro(technology):
        if technology not in tech_macros:
            raise ValueError(f"LaTeX macros config is missing a 'technologies' entry for '{technology}'")
        return "\\" + tech_macros[technology]['name']

    tests_by_name = {test['name']: test for test in manifest['tests']}
    base_names = _ordered_base_names(manifest['tests'])
    columns = _tech_columns(manifest.get('shex_technologies', []), manifest.get('shacl_technologies', []))
    unique_technologies = list(dict.fromkeys(technology for _, technology, _ in columns))

    results_index = {}
    for entry in results:
        key = (entry['name'], entry['engine_name'], entry['technology_name'])
        results_index[key] = entry['result']

    lines = []
    for category, spec in macros.items():
        lines.append(f"\\providecommand{{\\{spec['name']}}}{{{spec['latex']}}}")
    for technology in unique_technologies:
        lines.append(f"\\providecommand{{{tech_macro(technology)}}}{{{tech_macros[technology]['latex']}}}")
    lines.append("")
    lines.append("\\begin{table}")
    lines.append("\\centering")
    colspec = "l" + ("c" * len(columns)) + "|" + ("c" * 4)
    lines.append(f"\\begin{{tabular}}{{{colspec}}}")
    lines.append("\\hline")
    header = ["Test"] + [tech_macro(technology) + escape_latex(suffix) for _, technology, suffix in columns] + ["GFP", "LFP", "bSMS", "cSMS"]
    lines.append(" & ".join(header) + " \\\\")
    lines.append("\\hline")

    for base_name in base_names:
        variant_names = [name for name in tests_by_name if base_test_name(name) == base_name]
        row = [escape_latex(base_name)]
        for engine, technology, _suffix in columns:
            result = None
            for name in variant_names:
                result = results_index.get((name, engine, technology))
                if result is not None:
                    break
            row.append(macro(_engine_mark(result)))
        expected_results = {}
        for name in variant_names:
            expected_results = tests_by_name[name].get('expected_results', {})
            if expected_results:
                break
        marks = prescribed_marks(expected_results)
        row.extend(macro(marks[key]) for key in ('GFP', 'LFP', 'bSMS', 'cSMS'))
        lines.append(" & ".join(row) + " \\\\")

    lines.append("\\hline")
    lines.append("\\end{tabular}")
    if config.get('caption'):
        lines.append(f"\\caption{{{config['caption']}}}")
    if config.get('label'):
        lines.append(f"\\label{{{config['label']}}}")
    lines.append("\\end{table}")
    return "\n".join(lines) + "\n"


def save_results_latex(results, manifest, output, config_path):
    config = load_latex_config(config_path)
    table = build_latex_table(results, manifest, config)
    if output is not None:
        output_file = output + ".tex"
        with open(output_file, 'w') as file:
            file.write(table)
        return output_file
    else:
        print(table)
        return None

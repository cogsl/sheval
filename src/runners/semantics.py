"""
Compare a technology's validation result against the expected results declared
per semantics (lfp, gfp, sums, ...) in a test's manifest entry.

A semantics entry takes one of two forms:
- `models`: a list of candidate models, plus a `quantifier` ('any' or 'all').
  A model declares, explicitly, the pairs expected to pass and the pairs
  expected to fail; pairs mentioned in neither list are left unconstrained.
  With quantifier 'any' (brave), the semantics matches if the observed result
  agrees with at least one candidate model. With 'all' (cautious), it must
  agree with every candidate model simultaneously - which is only possible
  when the models don't disagree on any pair, since a single validator run
  can't produce more than one successes/failures split.
- `conforms`: a single expected boolean for the overall result, used for tests
  (e.g. non-stratified catalogues, unsatisfiable selectors) where the paper
  only prescribes an accept/reject verdict rather than per-pair models.
"""


def _pair_tuple(pair):
    return (pair['node'], pair['shape'])


def _pair_set(pairs):
    return set(_pair_tuple(pair) for pair in pairs)


def observed_pairs(result, all_pairs):
    """
    The (successes, failures) sets an engine reported for a test, as (node, shape)
    tuples, or None if the run didn't produce a usable result (error/exception/undefined).
    """
    conforms = result.get('conforms')
    if conforms not in (True, False):
        return None
    if 'successes' in result:
        successes = _pair_set(result['successes'])
        failures = _pair_set(result.get('failures', []))
    else:
        failures = _pair_set(result.get('failures', []))
        successes = all_pairs - failures
    return successes, failures


def _model_matches(model, successes, failures):
    expected_passing = _pair_set(model.get('passing', []))
    expected_failing = _pair_set(model.get('failing', []))
    return expected_passing <= successes and expected_failing <= failures


def match_expected_results(expected_results, all_pairs, result):
    """
    For each semantics declared in expected_results, check whether the engine's
    result agrees with it: either the reported successes/failures agree with one
    of its candidate models, or, for a 'conforms'-only entry, the overall
    conforms flag matches the expected boolean.
    return: dict mapping semantics name -> True/False, or None if the result
            couldn't be evaluated (e.g. the technology errored out)
    """
    conforms = result.get('conforms')
    observed = observed_pairs(result, all_pairs)
    matches = {}
    for name, semantics_entry in expected_results.items():
        if 'conforms' in semantics_entry:
            if conforms not in (True, False):
                matches[name] = None
            else:
                matches[name] = conforms == semantics_entry['conforms']
            continue
        if observed is None:
            matches[name] = None
            continue
        successes, failures = observed
        models = semantics_entry.get('models', [])
        quantifier = semantics_entry.get('quantifier', 'any')
        if quantifier == 'all':
            matches[name] = all(_model_matches(model, successes, failures) for model in models)
        else:
            matches[name] = any(_model_matches(model, successes, failures) for model in models)
    return matches


def all_interesting_pairs(nodes, shapes, pairs):
    """The full set of (node, shape) pairs a test declares, as the nodes x shapes cross product plus explicit pairs."""
    result = set()
    for node in nodes:
        for shape in shapes:
            result.add((node, shape))
    for pair in pairs:
        result.add(_pair_tuple(pair))
    return result

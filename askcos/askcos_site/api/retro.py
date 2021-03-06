from django.http import JsonResponse
from makeit import global_config as gc
from makeit.utilities.banned import BANNED_SMILES
from askcos_site.askcos_celery.treebuilder.tb_c_worker import get_top_precursors as get_top_precursors_c
from askcos_site.main.views.users import can_avoid_banned_chemicals

TIMEOUT = 30
TIMEOUT_ALL = 60


def is_banned(request, smiles):
    if can_avoid_banned_chemicals(request):
        return False
    if smiles in BANNED_SMILES:
        return True
    return False


def singlestep(request):
    resp = {}
    resp['request'] = dict(**request.GET)
    run_async = request.GET.get('async', False)
    target = request.GET.get('target')

    if is_banned(request, target):
        resp['error'] = 'ASKCOS does not provide results for compounds on restricted lists such as the CWC and DEA schedules'
        return JsonResponse(resp, status=400)

    template_prioritization = request.GET.get('template_prioritization', gc.relevance)
    precursor_prioritization = request.GET.get('precursor_prioritization', gc.relevanceheuristic)
    mincount = int(request.GET.get('mincount', 0))
    num_templates = int(request.GET.get('num_templates', 100))
    max_cum_prob = float(request.GET.get('max_cum_prob', 0.995))
    if request.GET.get('apply_fast_filter'):
        apply_fast_filter = request.GET.get('apply_fast_filter') in ['True', 'true']
    else:
        apply_fast_filter = True
    filter_threshold = float(request.GET.get('filter_threshold', 0.75))
    max_branching = int(request.GET.get('num_results', 100))
    res = get_top_precursors_c.delay(
        target,
        template_prioritization,
        precursor_prioritization,
        mincount=mincount,
        apply_fast_filter=apply_fast_filter,
        filter_threshold=filter_threshold,
        max_branching=max_branching,
        max_cum_prob=max_cum_prob
    )

    if run_async:
        resp['id'] = res.id
        resp['state'] = res.state
        return JsonResponse(resp)

    if template_prioritization == gc.relevance:
        timeout = TIMEOUT
    else:
        timeout = TIMEOUT_ALL

    try:
        (smiles, precursors) = res.get(timeout)
    except:
        resp['error'] = 'API request timed out (limit {}s)'.format(timeout)
        res.revoke()
        return JsonResponse(resp, 500)

    resp['precursors'] = precursors
    for precursor in precursors:
        precursor['templates'] = precursor.pop('tforms')
    return JsonResponse(resp)

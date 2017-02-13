import asyncio
from unittest.mock import Mock, patch

from asynctest import CoroutineMock
import pytest


def test_urgent():
    from jenkins_epo.repository import PullRequest

    pr1 = PullRequest(payload=dict(
        head=dict(sha='01234567899abcdef', ref='pr1'),
        number=1, html_url='pulls/1',
    ), repository=Mock())
    assert not pr1.urgent
    pr2_urgent = PullRequest(payload=dict(
        head=dict(sha='01234567899abcdef', ref='pr2'),
        title='[URGENT] urgent',
        number=2, html_url='pulls/2',
    ), repository=Mock())
    assert pr2_urgent.urgent

    assert pr1.sort_key() > pr2_urgent.sort_key()


@pytest.mark.asyncio
@asyncio.coroutine
def test_wrong_url(mocker):
    from jenkins_epo.repository import Head

    with pytest.raises(Exception):
        yield from Head.from_url('https://github.com/owner/name')


@pytest.mark.asyncio
@asyncio.coroutine
def test_branch_from_url(mocker):
    cached_arequest = mocker.patch(
        'jenkins_epo.repository.cached_arequest', CoroutineMock()
    )
    mocker.patch('jenkins_epo.repository.Repository')
    Branch = mocker.patch('jenkins_epo.repository.Branch')

    cached_arequest.return_value = {'protected': True}

    from jenkins_epo.repository import Head

    head = yield from Head.from_url('https://github.com/own/name/tree/master')
    assert head == Branch.return_value


@pytest.mark.asyncio
@asyncio.coroutine
def test_pr_from_url(mocker):
    mocker.patch('jenkins_epo.repository.cached_arequest', CoroutineMock())
    mocker.patch('jenkins_epo.repository.Repository')
    PullRequest = mocker.patch('jenkins_epo.repository.PullRequest')

    from jenkins_epo.repository import Head

    head = yield from Head.from_url('https://github.com/own/name/pull/1')
    assert head == PullRequest.return_value


@pytest.mark.asyncio
@asyncio.coroutine
def test_pr_from_branch_url(mocker):
    cached_arequest = mocker.patch(
        'jenkins_epo.repository.cached_arequest', CoroutineMock()
    )
    from_name = mocker.patch(
        'jenkins_epo.repository.Repository.from_name', CoroutineMock()
    )
    PullRequest = mocker.patch('jenkins_epo.repository.PullRequest')

    from jenkins_epo.repository import Head

    cached_arequest.return_value = {'protected': False}
    from_name.return_value.fetch_pull_requests = CoroutineMock(
        return_value=[{'head': {
            'ref': 'pr',
            'repo': {'html_url': 'https://github.com/owner/name'},
        }}]

    )
    head = yield from Head.from_url('https://github.com/owner/name/tree/pr')
    assert head == PullRequest.return_value


@pytest.mark.asyncio
@asyncio.coroutine
def test_from_url_unprotected_branch_no_pr(mocker):
    cached_arequest = mocker.patch(
        'jenkins_epo.repository.cached_arequest', CoroutineMock()
    )
    from_name = mocker.patch(
        'jenkins_epo.repository.Repository.from_name', CoroutineMock()
    )

    from jenkins_epo.repository import Head

    cached_arequest.return_value = {'protected': False}
    from_name.return_value.fetch_pull_requests = CoroutineMock(
        return_value=[]
    )

    with pytest.raises(Exception):
        yield from Head.from_url('https://github.com/owner/name/tree/pr')

    assert from_name.mock_calls
    assert cached_arequest.mock_calls


@patch('jenkins_epo.repository.GITHUB')
def test_delete_branch(GITHUB):
    from jenkins_epo.repository import PullRequest

    GITHUB.dry = False

    pr = PullRequest(Mock(), payload=dict(head=dict(ref='x', sha='x')))
    pr.delete_branch()
    assert GITHUB.repos.mock_calls


@patch('jenkins_epo.repository.GITHUB')
def test_delete_branch_dry(GITHUB):
    from jenkins_epo.repository import PullRequest

    pr = PullRequest(Mock(), payload=dict(head=dict(ref='x', sha='x')))
    pr.delete_branch()
    assert not GITHUB.repos.mock_calls


def test_sort_heads():
    from jenkins_epo.repository import Branch, PullRequest

    master = Branch(Mock(), dict(name='master', commit=dict(sha='d0d0')))
    pr = PullRequest(Mock(), dict(
        head=dict(ref='pr', sha='d0d0'), number=1, html_url='pr',
    ))
    urgent_pr = PullRequest(Mock(), dict(
        head=dict(ref='urgent_pr', sha='d0d0'), number=2, html_url='urgent_pr',
    ))
    urgent_pr.urgent = True

    assert master < pr
    assert urgent_pr < pr
    assert master != pr

    heads = [master, pr, urgent_pr]

    computed = list(sorted(heads, key=lambda h: h.sort_key()))
    wanted = [urgent_pr, master, pr]

    assert wanted == computed


@patch('jenkins_epo.repository.cached_request')
def test_branch_fetch_previous_commits(cached_request):
    cached_request.side_effect = [
        dict(parents=[dict(sha='d0d0cafe')]),
        dict()
    ]
    from jenkins_epo.repository import Branch

    head = Branch(Mock(), dict(name='branch', commit=dict(sha='d0d0cafe')))
    assert list(head.fetch_previous_commits())
    assert cached_request.mock_calls


@patch('jenkins_epo.repository.cached_request')
def test_pr_fetch_previous_commits(cached_request):
    from jenkins_epo.repository import PullRequest
    cached_request.return_value = dict(commits=['previous', 'last'])
    head = PullRequest(Mock(), dict(
        head=dict(ref='pr', sha='d0d0cafe', label='owner:pr'),
        base=dict(label='owner:base'),
    ))
    commits = list(head.fetch_previous_commits())
    assert ['last', 'previous'] == commits


@patch('jenkins_epo.repository.cached_request')
def test_pr_list_comments(cached_request):
    from jenkins_epo.repository import PullRequest

    cached_request.return_value = []
    pr = PullRequest(Mock(), dict(
        created_at='2017-01-20 11:08:43Z',
        number=204,
        head=dict(ref='pr', sha='d0d0cafe', label='owner:pr'),
    ))
    comments = pr.list_comments()
    assert 1 == len(comments)

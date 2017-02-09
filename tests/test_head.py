import asyncio

from asynctest import CoroutineMock
import pytest


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

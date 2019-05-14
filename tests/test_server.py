from click.testing import CliRunner
import flask
import pytest

from bukuserver import server
from bukuserver.response import response_template

@pytest.mark.parametrize(
    'args,word',
    [
        ('--help', 'bukuserver'),
        ('--version', 'Buku')
    ]
)
def test_cli(args, word):
    runner = CliRunner()
    result = runner.invoke(server.cli, [args])
    assert result.exit_code == 0
    assert word in result.output


@pytest.fixture
def client(tmp_path):
    test_db = tmp_path / 'test.db'
    app = server.create_app(test_db.as_posix())
    client = app.test_client()
    return client


def test_home(client):
    rd = client.get('/')
    assert rd.status_code == 200
    assert not flask.g.bukudb.get_rec_all()


@pytest.mark.parametrize(
    'url, exp_res', [
        ['/api/tags', {'tags': []}],
        ['/api/bookmarks', {'bookmarks': []}],
        ['/api/bookmarks/search', {'bookmarks': []}],
        ['/api/bookmarks/refresh', response_template['failure']]
    ]
)
def test_api_empty_db(client, url, exp_res):
    if url == '/api/bookmarks/refresh':
        rd = client.post(url)
        assert rd.status_code == 400
    else:
        rd = client.get(url)
        assert rd.status_code == 200
    assert rd.get_json() == exp_res


@pytest.mark.parametrize(
    'url, exp_res, status_code, method', [
        ['/api/tags/1', {'message': 'This resource does not exist.'}, 404, 'get'],
        ['/api/tags/1', response_template['failure'], 400, 'put'],
        ['/api/bookmarks/1', response_template['failure'], 400, 'get'],
        ['/api/bookmarks/1', response_template['failure'], 400, 'put'],
        ['/api/bookmarks/1', response_template['failure'], 400, 'delete'],
        ['/api/bookmarks/1/refresh', response_template['failure'], 400, 'post'],
    ]
)
def test_invalid_id(client, url, exp_res, status_code, method):
    rd = getattr(client, method)(url)
    assert rd.status_code == status_code
    assert rd.get_json() == exp_res


def test_tag_api(client):
    url = 'http://google.com'
    rd = client.post('/api/bookmarks', data={'url': url, 'tags': 'tag1,tag2'})
    assert rd.status_code == 200
    assert rd.get_json() == response_template['success']
    rd = client.get('/api/tags')
    assert rd.status_code == 200
    assert rd.get_json() == {'tags': ['tag1', 'tag2']}
    rd = client.get('/api/tags/tag1')
    assert rd.status_code == 200
    assert rd.get_json() == {'name': 'tag1', 'usage_count': 1}
    rd = client.put('/api/tags/tag1', data={'tags': 'tag3,tag4'})
    assert rd.status_code == 200
    assert rd.get_json() == response_template['success']
    rd = client.get('/api/tags')
    assert rd.status_code == 200
    assert rd.get_json() == {'tags': ['tag2', 'tag3 tag4']}
    rd = client.put('/api/tags/tag2', data={'tags': 'tag5'})
    assert rd.status_code == 200
    assert rd.get_json() == response_template['success']
    rd = client.get('/api/tags')
    assert rd.status_code == 200
    assert rd.get_json() == {'tags': ['tag3 tag4', 'tag5']}
    rd = client.get('/api/bookmarks/1')
    assert rd.status_code == 200
    assert rd.get_json() == {
        'description': '', 'tags': ['tag3 tag4', 'tag5'], 'title': '',
        'url': 'http://google.com'}


def test_bookmark_api(client):
    url = 'http://google.com'
    rd = client.post('/api/bookmarks', data={'url': url})
    assert rd.status_code == 200
    assert rd.get_json() == response_template['success']
    rd = client.post('/api/bookmarks', data={'url': url})
    assert rd.status_code == 400
    assert rd.get_json() == response_template['failure']
    rd = client.get('/api/bookmarks')
    assert rd.status_code == 200
    assert rd.get_json() == {'bookmarks': [{
        'description': '', 'tags': [], 'title': '', 'url': 'http://google.com'}]}
    rd = client.get('/api/bookmarks/1')
    assert rd.status_code == 200
    assert rd.get_json() == {
        'description': '', 'tags': [], 'title': '', 'url': 'http://google.com'}
    rd = client.put('/api/bookmarks/1', data={'tags': [',tag1,tag2,']})
    assert rd.status_code == 200
    assert rd.get_json() == response_template['success']
    rd = client.get('/api/bookmarks/1')
    assert rd.status_code == 200
    assert rd.get_json() == {
        'description': '', 'tags': ['tag1', 'tag2'], 'title': '', 'url': 'http://google.com'}


@pytest.mark.parametrize('d_url', ['/api/bookmarks', '/api/bookmarks/1'])
def test_bookmark_api_delete(client, d_url):
    url = 'http://google.com'
    rd = client.post('/api/bookmarks', data={'url': url})
    assert rd.status_code == 200
    assert rd.get_json() == response_template['success']
    rd = client.delete(d_url)
    assert rd.status_code == 200
    assert rd.get_json() == response_template['success']


@pytest.mark.parametrize('api_url', ['/api/bookmarks/refresh', '/api/bookmarks/1/refresh'])
def test_refresh_bookmark(client, api_url):
    url = 'http://google.com'
    rd = client.post('/api/bookmarks', data={'url': url})
    assert rd.status_code == 200
    assert rd.get_json() == response_template['success']
    rd = client.post(api_url)
    assert rd.status_code == 200
    assert rd.get_json() == response_template['success']
    rd = client.get('/api/bookmarks/1')
    assert rd.status_code == 200
    assert rd.get_json() == {
        'description': '', 'tags': [], 'title': 'Google', 'url': 'http://google.com'}

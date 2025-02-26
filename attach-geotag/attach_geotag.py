import sys
import time
from tqdm import tqdm
sys.path.append("..")
from common import retryable_authorized_http_requests, jsons_dir
from microdb import MicroDB
from calc_geotag import calc_geotag

class DeletedUserException(Exception):
    pass

def username_to_location(username="umihico"):
    url = f'https://api.github.com/users/{username}'
    response = retryable_authorized_http_requests(url)
    json=response.json()
    if 'location' in json:
        return response.json()['location']
    elif 'message' in json and json['message']=="Not Found":
        raise DeletedUserException()
    else:
        raise Exception(f'unknown response:{str(json)}')



def test_username_to_location():
    print(username_to_location())


def update(username, mdb_geotag):
    try:
        location = username_to_location(username)
    except DeletedUserException as e:
        return
    else:
        geotag_json = {
            "username": username,
            'last_modified': time.time(),
            'raw': location,
            'geotags': calc_geotag(location)
        }
        print(username, location, calc_geotag(location))
        mdb_geotag.upsert(geotag_json)
        mdb_geotag.save()


def sort_by_priotity(mdb_repos, mdb_geotag):
    last_modified_time_dict = {}
    for repo in mdb_repos.all():
        username = repo['username']
        if repo in mdb_geotag:
            geotag_json = mdb_geotag.get(repo)
            last_modified = geotag_json['last_modified']
        else:
            # print(username)
            last_modified = 0
            geotag_json = {}
        last_modified_time_dict[username] = last_modified
    usernames_times = list(last_modified_time_dict.items())
    usernames_times.sort(key=lambda x: x[1])
    usernames = [username for username, time_ in usernames_times]
    return usernames


def attach_all_geotag(count=100):
    mdb_repos = MicroDB(jsons_dir+'repos.json', partition_keys=['username', ])
    mdb_geotag = MicroDB(jsons_dir+'geotag.json', partition_keys=['username', ])
    sorted_usernames_by_priotity = sort_by_priotity(mdb_repos, mdb_geotag)
    for username in tqdm(sorted_usernames_by_priotity[:count]):
        update(username, mdb_geotag)
    i = 0

    for d in mdb_repos.all():
        geotag = mdb_geotag.get(d)
        if geotag is None:
            i += 1
            print(i, d)


if __name__ == '__main__':
    # test_username_to_location()
    import sys
    sys.argv
    upto = int(sys.argv[1]) if len(sys.argv) >= 2 else 100
    attach_all_geotag(upto)

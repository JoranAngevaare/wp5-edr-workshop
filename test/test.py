import pydantic
from typing import List, Optional

from covjson_pydantic.ndarray import NdArrayFloat

from fastapi import FastAPI
from fastapi.testclient import TestClient
from main import app


client = TestClient(app)


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200

def read_station_minimal():
    response = client.get("/collections/observations/locations/0-20000-0-06260")
    assert response.status_code == 200


def test_read_station():
    response = client.get("/collections/observations/locations/0-20000-0-06260?parameter-name=ff%2C%20dd&datetime=2024-02-22T01%3A00%3A00Z%2F2024-02-22T02%3A00%3A00Z")
    assert response.status_code == 200
    


def test_read_bad_station():
    response = client.get("/collections/observations/locations/my_home")
    assert response.status_code == 400
    assert "my_home is not in" in response.json()['detail'], response.json()
    
def test_read_bad_var():
    response = client.get("/collections/observations/locations/0-20000-0-06260?parameter-name=my_variable")
    assert response.status_code == 400
    assert "Only unknown parameters" in response.json()['detail'], response.json()
    
def test_read_bad_and_good_var():
    response = client.get("/collections/observations/locations/0-20000-0-06260?parameter-name=my_variable%2C%20ff")
    assert response.status_code == 200, response.json()['detail']


def test_bad_datestation():
    response = client.get("/collections/observations/locations/0-20000-0-06260?datetime=2024-02-22T01%3A00%3A00Z%2F2024-00-22T02%3A00%3A00Z")
    assert response.status_code == 400, response.json()
    assert 'One or more invalid date values' in response.json()['detail'], response.json()
    
def test_bad_time_slice():
    response = client.get("/collections/observations/locations/0-20000-0-06260?datetime=2025-02-22T01%3A00%3A00Z%2F2024-00-22T02%3A00%3A00Z")
    assert response.status_code == 400, response.json()
    
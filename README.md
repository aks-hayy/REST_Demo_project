# REST_Demo_project
Assumptions and Adjustments I made :
1. Added the reason column and parameter to the Product Table and the StockUpdate API to record the reason why the stock was updated
2.Assumed that ids of the tables will be called often so indexed those id attributes
3.The API key used for the X-api-key header is currently a dummy value. Can be changed to a system variable or can be kept in a secret manager.

You can run the app by running
uvicorn main:app --reload  in the directory where this code is cloned into

You can build the docker container by running 
docker compose up --build -d 
from the root directory where this code is cloned into

You can run the tests by runnng
python -m pytest -v
from the root directory where this code is cloned into after installation.



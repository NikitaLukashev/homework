# Context
We construct an ML model that predict the time to sell a product on Label Emmaüs marketplace.
It's a standard classification problem with 3 classes.
We will use log loss metric during train, and predict a probability for each class during a prediction.

# Dataset
Dataset for training is in './data/data.csv', it contains 8880 Emmaus product(8880 columns).
Each line describe a product and the time to sell it, so each row contains the following fields : 
 - our base feature: id,nb_images,longueur_image,largeur_image,description_produit,annee,couleur,prix,categorie,nom_produit
 - our target: delai_vente contains value 0(fast to sell), 1(normal time to sell, 2(very long time to sell) 

# Modelisation
We generate some base feature like tf-idf, label encoding.

# ML
Our problem is a 3 classes classification problem.
We train a supervised RandomForestClassifier on the full dataset and save it into the db.
 
I don't create complexe feature, grid search, pamameter optimisation, as 
the score is not important for this test.


# Product testing
Create .env file in allisone with similar content of the .env.example. 
It contents your db secret like POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB and DATABASE uri, 
you can change those value in .env to your secrets. Never commit .env file, 
your secrets can be stealed.
```shellscript
cp .env.example .env
```


Test are run in docker container. File test.Dockerfile execute pytest test. 
As product use relational db postgresql@14.1, you should deploy the container with db
before running test. 
There is 9 unit test to check API route, controller and db state change on API call.
To run test:
```shellscript
docker-compose -f test.docker-compose.yml up
```
After that you should see:
 ======================= 9 passed, 11 warnings in 22.06s ========================

# Product deployment
Deploy the docker-compose.yml file, it will instanciate postgresql@14.1 and deploy 
the web app.
Open a new terminal in the project root and run
```shellscript
docker-compose -f docker-compose.yml up
```

An ML model is automatically trained, you can start interacting with the api

# Database modelisation
Our database contains 3 tables, it's modeled for the purpose of:
 - storing and versioning different ml algorythm
 - storing ml prediction and bind theme to ml model version for A/B testing different model version
 - storing train data to train and retrain our algorythm

There are 3 tables:
 - catalog which contains initial train data
 - predictions which contains input data, ML prediction and ML model version
 - snapshots which contains trained ML model and associated feature transformer

You can bind ml model from snapshots table and prediction from predictions 
table by foreign key model_id from predictions table and primary key id from 
snapshots table. And so retrieve all prediction by model and start AB test.
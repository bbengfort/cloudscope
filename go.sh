#!/bin/bash

python scope.py traces -u 20 -o 30 -t 4320000 deploy/data/federated/federated.json -w fixtures/experiments/federated/conflict/traces/realism-federated-0.0-pconflict.tsv -c 0.0
python scope.py traces -u 20 -o 30 -t 4320000 deploy/data/federated/federated.json -w fixtures/experiments/federated/conflict/traces/realism-federated-0.1-pconflict.tsv -c 0.1
python scope.py traces -u 20 -o 30 -t 4320000 deploy/data/federated/federated.json -w fixtures/experiments/federated/conflict/traces/realism-federated-0.2-pconflict.tsv -c 0.2
python scope.py traces -u 20 -o 30 -t 4320000 deploy/data/federated/federated.json -w fixtures/experiments/federated/conflict/traces/realism-federated-0.3-pconflict.tsv -c 0.3
python scope.py traces -u 20 -o 30 -t 4320000 deploy/data/federated/federated.json -w fixtures/experiments/federated/conflict/traces/realism-federated-0.4-pconflict.tsv -c 0.4
python scope.py traces -u 20 -o 30 -t 4320000 deploy/data/federated/federated.json -w fixtures/experiments/federated/conflict/traces/realism-federated-0.5-pconflict.tsv -c 0.5
python scope.py traces -u 20 -o 30 -t 4320000 deploy/data/federated/federated.json -w fixtures/experiments/federated/conflict/traces/realism-federated-0.6-pconflict.tsv -c 0.6
python scope.py traces -u 20 -o 30 -t 4320000 deploy/data/federated/federated.json -w fixtures/experiments/federated/conflict/traces/realism-federated-0.7-pconflict.tsv -c 0.7
python scope.py traces -u 20 -o 30 -t 4320000 deploy/data/federated/federated.json -w fixtures/experiments/federated/conflict/traces/realism-federated-0.8-pconflict.tsv -c 0.8
python scope.py traces -u 20 -o 30 -t 4320000 deploy/data/federated/federated.json -w fixtures/experiments/federated/conflict/traces/realism-federated-0.9-pconflict.tsv -c 0.9
python scope.py traces -u 20 -o 30 -t 4320000 deploy/data/federated/federated.json -w fixtures/experiments/federated/conflict/traces/realism-federated-1.0-pconflict.tsv -c 1.0

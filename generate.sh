#!/bin/bash 

BASE=fixtures/experiments/federated/latency
TRACE=$BASE/moderate-conflict-workload.tsv 
TOPO=deploy/data/federated

# Howard Model Eventual Sequence 
python scope.py generate -f -g federated --traces $TRACE --users 20,20,1 --tick-metric howard -o $BASE/howard/low/ \
	--latency 20,1000,80 -n 12 $TOPO/eventual.json 
python scope.py generate -f -g federated --traces $TRACE --users 20,20,1 --tick-metric howard -o $BASE/howard/medium/ \
	--latency 1000,2000,160 -n 12 $TOPO/eventual.json 
python scope.py generate -f -g federated --traces $TRACE --users 20,20,1 --tick-metric howard -o $BASE/howard/high/ \
	--latency 2000,3000,240 -n 12 $TOPO/eventual.json 

# Howard Model Federated Sequence 
python scope.py generate -f -g federated --traces $TRACE --users 20,20,1 --tick-metric howard -o $BASE/howard/low/ \
	--latency 20,1000,80 -n 12 $TOPO/federated.json 
python scope.py generate -f -g federated --traces $TRACE --users 20,20,1 --tick-metric howard -o $BASE/howard/medium/ \
	--latency 1000,2000,160 -n 12 $TOPO/federated.json 
python scope.py generate -f -g federated --traces $TRACE --users 20,20,1 --tick-metric howard -o $BASE/howard/high/ \
	--latency 2000,3000,240 -n 12 $TOPO/federated.json 

# Howard Model Sequential Sequence 
python scope.py generate -f -g federated --traces $TRACE --users 20,20,1 --tick-metric howard -o $BASE/howard/low/ \
	--latency 20,1000,80 -n 12 $TOPO/sequential.json 
python scope.py generate -f -g federated --traces $TRACE --users 20,20,1 --tick-metric howard -o $BASE/howard/medium/ \
	--latency 1000,2000,160 -n 12 $TOPO/sequential.json 
python scope.py generate -f -g federated --traces $TRACE --users 20,20,1 --tick-metric howard -o $BASE/howard/high/ \
	--latency 2000,3000,240 -n 12 $TOPO/sequential.json 

# Bailis Model Eventual Sequence 
python scope.py generate -f -g federated --traces $TRACE --users 20,20,1 --tick-metric bailis -o $BASE/bailis/low/ \
	--latency 20,1000,80 -n 12 $TOPO/eventual.json 
python scope.py generate -f -g federated --traces $TRACE --users 20,20,1 --tick-metric bailis -o $BASE/bailis/medium/ \
	--latency 1000,2000,160 -n 12 $TOPO/eventual.json 
python scope.py generate -f -g federated --traces $TRACE --users 20,20,1 --tick-metric bailis -o $BASE/bailis/high/ \
	--latency 2000,3000,240 -n 12 $TOPO/eventual.json 

# Bailis Model Federated Sequence 
python scope.py generate -f -g federated --traces $TRACE --users 20,20,1 --tick-metric bailis -o $BASE/bailis/low/ \
	--latency 20,1000,80 -n 12 $TOPO/federated.json 
python scope.py generate -f -g federated --traces $TRACE --users 20,20,1 --tick-metric bailis -o $BASE/bailis/medium/ \
	--latency 1000,2000,160 -n 12 $TOPO/federated.json 
python scope.py generate -f -g federated --traces $TRACE --users 20,20,1 --tick-metric bailis -o $BASE/bailis/high/ \
	--latency 2000,3000,240 -n 12 $TOPO/federated.json 

# Bailis Model Sequential Sequence 
python scope.py generate -f -g federated --traces $TRACE --users 20,20,1 --tick-metric bailis -o $BASE/bailis/low/ \
	--latency 20,1000,80 -n 12 $TOPO/sequential.json 
python scope.py generate -f -g federated --traces $TRACE --users 20,20,1 --tick-metric bailis -o $BASE/bailis/medium/ \
	--latency 1000,2000,160 -n 12 $TOPO/sequential.json 
python scope.py generate -f -g federated --traces $TRACE --users 20,20,1 --tick-metric bailis -o $BASE/bailis/high/ \
	--latency 2000,3000,240 -n 12 $TOPO/sequential.json 

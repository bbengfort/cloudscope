# Consistency Validation

In order to verify that replicas are appending writes correctly to their logs, we have created a consistency validation reporter that can optionally be run at the end of a simulation (optional because it takes a lot of time to run). This document describes the consistency reporting and presents results for the current stable versions of replication models in the simulation.

Bermbach and Kuhlenkamp describe consistency along two dimensions: _staleness_ and _ordering_ from both client and data perspectives. Of these, they posit that _ordering_ is more important and that stricter ordering tends to lead to increased _staleness_. Because of this priority and the fact that staleness is a runtime metric, our post-processing validation focuses on the inspection of the ordering and contents of writes in each individual replica server's log.

Each replica server maintains an ordered log of _writes_ that is appended to according to its replication and consistency policies. Each write contains the _name_ of the object being written to, a _version_ number that uniquely identifies the write, and a _parent_ from which the write was derived. Logs therefore contain version trees/histories for multiple objects in the data namespace. _Reads_ are typically executed by a reverse search for the given name in the log, returning the last appended version for that named object.

## Metrics

The consistency report validates the simulation in two ways:

1. Per-log analysis for each replica server
2. Pairwise log to log comparisons for each replica server combination.

Note that currently these metrics only take into account the entries that are in the logs and ignore any entry that is not in a replica server's log (e.g. dropped or unavailable writes).

### Single Log Metrics

An analysis of a single log allows us to compute the following metrics:

- **Entries**: the total number of elements in the log.
- **Forks**: count the total number of versions in the log who have multiple children.
- **Monotonically Increasing Errors**: on a per-name basis, ensure that the next entry in the log has a version number that is greater than the previous one.
- **Duplicates**: determine if the same entry has been appended to the log more than once.
- **Missing**: given the latest version number for an object, determine how many entries are not in the log.

The missing metric is the least reliable since it only compares the number of entries to the latest version number, which could be incremented without implying a new version. Single log metrics cannot account for dropped or unavailable writes since the metric does not have global knowledge.

### Pairwise Log Metrics

We compare two logs via the following normalized distance metrics (where 0.0 is identical and 1.0 is completely different):

- **Jaccard**: the ratio of the intersection of the entries in the log to the union of the entries. This metric simply compares the contents of the log, e.g. whether or not they contain the same entries duplicated or not.
- **Levenshtein**: also called the edit distance, this metric counts the minimum number of insertions, deletions, and substitutions that will convert one log to another. This distance metric considers ordering and duplication as well as content of both logs.

Both distance metrics are normalized to the space between 0 and 1, where 0 is identical. Note that the pairwise metrics are presented as a square array of distances where the lower-left triangle is Jaccard distance and the upper right triangle is Levenshtein distance (the diagonal will always be zero).

## Consistency Results

In this section, we present the consistency validation reports for the following consistency/replication models:

- Homogenous Raft (sequential consistency)
- Homogenous Bilateral Anti-Entropy (eventual consistency)
- Federated Raft and Bilateral Anti-Entropy (federated consistency)

Each report includes the per-log discrepancy tables for the metrics described above, as well as the log distance matrix for both Jaccard and Levenshtein distances.

### Homogenous Raft

Sequential consistency implies no forks, no duplicates, and no misordering. Because we are using consensus, Raft also implies that the logs of each replica should be identical, with only minor variability in the difference between a leader's log and follower's logs (due to the system being cut off before the arrival of `AppendEntries`).

Timing was as follows:

- Simulation took 11 seconds
- Consistency validation took 6 minutes 15 seconds

The simulation consisted of 20 nodes in 5 areas (a-e), 4 nodes per area with a local area latency normally distributed as 30μ, 5σ ms and a wide area latency normally distributed as 300μ, 50σ ms. The simulation ran for 15 simulated minutes and traced 5,995 accesses (both reads and writes) across 114 objects with a conflict likelihood of 0.4.

#### Raft Per Log Consistency Report

```
name      entries    forks    monoincr errors    duplicates    missing
------  ---------  -------  -----------------  ------------  ---------
a0           2772        0                  0             0         87
a1           2772        0                  0             0         87
a2           2772        0                  0             0         87
a3           2772        0                  0             0         87
b0           2772        0                  0             0         87
b1           2772        0                  0             0         87
b2           2772        0                  0             0         87
b3           2772        0                  0             0         87
c0           2772        0                  0             0         87
c1           2772        0                  0             0         87
c2           2772        0                  0             0         87
c3           2772        0                  0             0         87
d0           2772        0                  0             0         87
d1           2774        0                  0             0         85
d2           2772        0                  0             0         87
d3           2772        0                  0             0         87
e0           2772        0                  0             0         87
e1           2772        0                  0             0         87
e2           2772        0                  0             0         87
e3           2772        0                  0             0         87
total        2859        0                  0             0       1738
```

As expected, Raft contains no forks, monotonically increasing errors, or duplicates. The 87 missing entries can be dropped writes (and are therefore never inserted into the log) or unavailable writes -- writes that occurred before a leader was elected. Note that the total number of entries is the sum of the latest version number for each object.

#### Raft Split Log Distance Report (Jaccard and Levenshtein)

```
J↓ L→      a0    a1    a2    a3    b0    b1    b2    b3    c0    c1    c2    c3    d0    d1    d2    d3    e0    e1    e2    e3
-------  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----
a0          0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0
a1          0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0
a2          0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0
a3          0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0
b0          0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0
b1          0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0
b2          0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0
b3          0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0
c0          0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0
c1          0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0
c2          0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0
c3          0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0
d0          0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0
d1          0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0
d2          0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0
d3          0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0
e0          0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0
e1          0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0
e2          0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0
e3          0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0     0
```

In this case the simulation was terminated right after an `AppendEntries` and before any new `RemoteWrite` RPCs; therefore the logs are all completely identical.

### Homogenous Eventual

Eventual consistency implies that forks can be appended to the log and that logs may differ from each other in that one log may have an entry that another one does not. However, eventual logs should have monotonically increasing version numbers and no duplicates due to the "last writer wins" policy.

Timing was as follows:

- Simulation took 35 minutes 15 seconds
- Consistency validation took 44 minutes 34 seconds

The simulation consisted of 20 nodes in 5 areas (a-e), 4 nodes per area with a local area latency normally distributed as 30μ, 5σ ms and a wide area latency normally distributed as 300μ, 50σ ms. The simulation ran for 15 simulated minutes and traced 5,995 accesses (both reads and writes) across 114 objects with a conflict likelihood of 0.4.

#### Eventual Per Log Consistency Report

```
name      entries    forks    monoincr errors    duplicates    missing
------  ---------  -------  -----------------  ------------  ---------
a0           2802      123                  0             0         39
a1           2789      123                  0             0         78
a2           2804      123                  0             0         63
a3           2792      124                  0             0         75
b0           2799      125                  0             0         39
b1           2786      126                  0             0         52
b2           2786      126                  0             0         52
b3           2798      124                  0             0         40
c0           2800      125                  0             0         38
c1           2794      125                  0             0         18
c2           2797      122                  0             0         70
c3           2807      124                  0             0          5
d0           2799      124                  0             0         13
d1           2792      126                  0             0         46
d2           2787      125                  0             0         25
d3           2791      124                  0             0         47
e0           2796      125                  0             0         42
e1           2799      125                  0             0         13
e2           2799      125                  0             0         13
e3           2796      125                  0             0         42
total        2869     2489                  0             0        810
```

As you can see, all the eventual logs are slightly different and they contain forks and missing writes. However there are no duplicates nor any monotonically increasing version number errors.

#### Eventual Split Log Distance Report (Jaccard and Levenshtein)

```
J↓ L→      a0    a1    a2    a3    b0    b1    b2    b3    c0    c1    c2    c3    d0    d1    d2    d3    e0    e1    e2    e3
-------  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----
a0       0     0.6   0.59  0.6   0.72  0.72  0.72  0.73  0.73  0.73  0.73  0.73  0.72  0.72  0.72  0.72  0.73  0.72  0.74  0.73
a1       0.02  0     0.61  0.6   0.73  0.74  0.74  0.72  0.73  0.72  0.73  0.73  0.73  0.73  0.74  0.72  0.72  0.72  0.72  0.73
a2       0.02  0.02  0     0.59  0.73  0.72  0.72  0.73  0.73  0.73  0.73  0.74  0.72  0.71  0.72  0.71  0.73  0.73  0.73  0.73
a3       0.02  0.02  0.02  0     0.73  0.73  0.72  0.73  0.73  0.73  0.73  0.73  0.72  0.73  0.72  0.72  0.72  0.72  0.72  0.73
b0       0.03  0.04  0.03  0.03  0     0.6   0.61  0.61  0.74  0.72  0.73  0.73  0.73  0.73  0.74  0.74  0.72  0.74  0.72  0.74
b1       0.03  0.04  0.03  0.04  0.03  0     0.6   0.61  0.73  0.73  0.73  0.72  0.73  0.73  0.73  0.73  0.72  0.72  0.72  0.73
b2       0.03  0.04  0.04  0.04  0.03  0.03  0     0.61  0.73  0.72  0.73  0.72  0.73  0.73  0.73  0.74  0.72  0.72  0.72  0.73
b3       0.03  0.04  0.03  0.04  0.02  0.03  0.03  0     0.74  0.71  0.73  0.73  0.73  0.72  0.72  0.73  0.72  0.72  0.73  0.73
c0       0.03  0.04  0.03  0.04  0.03  0.03  0.04  0.03  0     0.6   0.59  0.6   0.73  0.73  0.73  0.73  0.72  0.73  0.72  0.72
c1       0.03  0.04  0.03  0.03  0.03  0.04  0.03  0.04  0.02  0     0.6   0.59  0.72  0.73  0.72  0.71  0.72  0.73  0.72  0.73
c2       0.03  0.04  0.03  0.03  0.03  0.04  0.04  0.03  0.02  0.02  0     0.6   0.72  0.73  0.72  0.72  0.73  0.73  0.73  0.72
c3       0.03  0.04  0.03  0.03  0.03  0.04  0.04  0.03  0.02  0.02  0.02  0     0.72  0.72  0.73  0.71  0.72  0.73  0.73  0.73
d0       0.03  0.03  0.03  0.03  0.03  0.04  0.03  0.03  0.03  0.03  0.03  0.03  0     0.6   0.6   0.6   0.73  0.73  0.72  0.73
d1       0.03  0.04  0.03  0.04  0.03  0.04  0.03  0.04  0.03  0.03  0.03  0.03  0.03  0     0.6   0.6   0.72  0.72  0.72  0.72
d2       0.03  0.04  0.03  0.03  0.03  0.04  0.04  0.04  0.03  0.03  0.03  0.03  0.02  0.02  0     0.6   0.72  0.73  0.73  0.73
d3       0.03  0.04  0.03  0.04  0.03  0.04  0.04  0.04  0.03  0.03  0.03  0.03  0.02  0.03  0.02  0     0.73  0.73  0.71  0.72
e0       0.03  0.04  0.03  0.04  0.03  0.03  0.04  0.03  0.03  0.03  0.03  0.03  0.03  0.03  0.04  0.03  0     0.6   0.6   0.6
e1       0.03  0.03  0.03  0.03  0.03  0.03  0.04  0.03  0.03  0.03  0.03  0.03  0.03  0.04  0.04  0.04  0.02  0     0.62  0.6
e2       0.03  0.03  0.03  0.03  0.03  0.03  0.03  0.03  0.03  0.03  0.03  0.03  0.03  0.03  0.03  0.03  0.02  0.02  0     0.61
e3       0.03  0.04  0.03  0.04  0.03  0.03  0.04  0.03  0.03  0.03  0.03  0.03  0.03  0.03  0.03  0.03  0.02  0.02  0.02  0
```

The eventual logs are different both in ordering and in contents. The Jaccard scores (the lower left triangle) show that the logs are pretty similar in their content. Some logs will be missing "stomped writes", e.g. a write that becomes stale (a newer version is written) before it is completely propagated.

The ordering distance measured by Levenshtein scores (the upper right triangle) shows that for the most part no two eventual logs are alike, though they may have small subsequences of correct ordering. Although there are no monotonically increasing errors or duplicates, this occurs because the ordering of writes to different objects and the missing values between two logs cause large discrepancies.

### Federated Raft and Eventual

The Federated model has four central nodes performing Raft consensus while the rest of the nodes are highly available eventual nodes. The goal of Federated is to reduce the ordering difference of logs and to create fewer forks. Like both Raft and Eventual, Federated should have no monotonically increasing errors and no duplicates in logs. It can, however, have forks (though hopefully far fewer than eventual) as well as missing entries (again, hopefully fewer than eventual). The pairwise log comparisons should also show that there are slightly less differences between the logs.

Timing was as follows:

- Simulation took 1 hour 26 minutes 45 seconds
- Consistency validation took 4 hours 34 minutes 47 seconds

The simulation consisted of 20 nodes in 5 areas (a-e), 4 nodes per area with a local area latency normally distributed as 30μ, 5σ ms and a wide area latency normally distributed as 300μ, 50σ ms. The simulation ran for 15 simulated minutes and traced 5,995 accesses (both reads and writes) across 114 objects with a conflict likelihood of 0.4.

#### Federated Per Log Consistency Report

```
name      entries    forks    monoincr errors    duplicates    missing
------  ---------  -------  -----------------  ------------  ---------
a0          11683        2                  0             0        104
a1           5269        1                  0             0       6518
a2           5337        0                  0             0       6450
a3           5422        1                  0             0       6365
b0          11683        2                  0             0        104
b1           5250        1                  0             0       6537
b2           5260        1                  0             0       6527
b3           5315        2                  0             0       6472
c0          11683        2                  0             0        104
c1           5225        0                  0             0       6535
c2           5302        2                  0             0       6458
c3           5268        1                  0             0       6519
d0          11695        2                  0             0         92
d1           5516        2                  0             0       6271
d2           5488        1                  0             0       6299
d3           5452        2                  0             0       6335
e0          11683        2                  0             0        104
e1           5226        1                  0             0       6534
e2           5242        0                  0             0       6545
e3           5282        2                  0             0       6478
total       11788       27                  0             0      97351
```

The "entries" metric became unreliable in Federated since I'm only counting the last version number, which is artificially inflated in order to integrate Federated and Raft; this also leads to the increasing in the missing number which now not only includes drops and unavailable writes, but also the skipped entries.

However, the number of forks is far less than in Eventual! So that's good news. The Raft nodes (all the `0` nodes, e.g. `a0` and `b0`) do have forks - but this simply could be that the entry was forked by a follower and has not yet made it to the leader to be dropped quite yet.

#### Federated Split Log Distance Report (Jaccard and Levenshtein)

```
J↓ L→      a0    a1    a2    a3    b0    b1    b2    b3    c0    c1    c2    c3    d0    d1    d2    d3    e0    e1    e2    e3
-------  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----  ----
a0       0     0.83  0.83  0.82  0     0.82  0.83  0.82  0     0.83  0.82  0.83  0     0.78  0.79  0.79  0     0.82  0.83  0.82
a1       0.55  0     0.71  0.71  0.83  0.77  0.79  0.75  0.83  0.76  0.75  0.77  0.83  0.77  0.76  0.77  0.83  0.77  0.77  0.76
a2       0.55  0.39  0     0.73  0.83  0.75  0.78  0.76  0.83  0.75  0.77  0.76  0.83  0.77  0.77  0.8   0.83  0.75  0.77  0.77
a3       0.54  0.38  0.38  0     0.82  0.77  0.77  0.78  0.82  0.75  0.76  0.76  0.82  0.79  0.79  0.79  0.82  0.75  0.75  0.76
b0       0     0.55  0.55  0.54  0     0.82  0.83  0.82  0     0.83  0.82  0.83  0     0.78  0.79  0.79  0     0.82  0.83  0.82
b1       0.55  0.36  0.35  0.36  0.55  0     0.76  0.73  0.82  0.76  0.76  0.75  0.83  0.77  0.76  0.79  0.82  0.75  0.78  0.75
b2       0.55  0.38  0.37  0.37  0.55  0.4   0     0.76  0.83  0.76  0.77  0.76  0.83  0.79  0.78  0.78  0.83  0.78  0.78  0.77
b3       0.55  0.36  0.38  0.37  0.55  0.38  0.42  0     0.82  0.76  0.78  0.76  0.82  0.77  0.77  0.78  0.82  0.76  0.76  0.77
c0       0     0.55  0.55  0.54  0     0.55  0.55  0.55  0     0.83  0.82  0.83  0     0.78  0.79  0.79  0     0.82  0.83  0.82
c1       0.56  0.37  0.35  0.36  0.56  0.36  0.36  0.37  0.56  0     0.74  0.74  0.83  0.78  0.77  0.77  0.83  0.76  0.77  0.76
c2       0.55  0.35  0.35  0.35  0.55  0.36  0.39  0.38  0.55  0.4   0     0.75  0.82  0.77  0.78  0.78  0.82  0.76  0.77  0.76
c3       0.55  0.36  0.35  0.36  0.55  0.35  0.36  0.37  0.55  0.37  0.4   0     0.83  0.76  0.77  0.77  0.83  0.75  0.77  0.77
d0       0     0.55  0.55  0.54  0     0.55  0.55  0.55  0     0.56  0.55  0.55  0     0.78  0.79  0.79  0     0.82  0.83  0.82
d1       0.53  0.37  0.36  0.35  0.53  0.36  0.37  0.36  0.53  0.37  0.35  0.36  0.53  0     0.73  0.73  0.78  0.77  0.78  0.76
d2       0.53  0.37  0.35  0.36  0.53  0.35  0.38  0.35  0.53  0.37  0.37  0.35  0.53  0.37  0     0.74  0.79  0.76  0.77  0.77
d3       0.53  0.36  0.37  0.37  0.53  0.37  0.38  0.37  0.53  0.37  0.37  0.37  0.54  0.38  0.39  0     0.79  0.78  0.77  0.78
e0       0     0.55  0.55  0.54  0     0.55  0.55  0.55  0     0.56  0.55  0.55  0     0.53  0.53  0.53  0     0.82  0.83  0.82
e1       0.56  0.37  0.35  0.36  0.56  0.35  0.37  0.38  0.56  0.37  0.37  0.35  0.56  0.38  0.35  0.38  0.56  0     0.75  0.75
e2       0.55  0.36  0.36  0.35  0.55  0.36  0.38  0.35  0.55  0.36  0.37  0.36  0.55  0.37  0.37  0.37  0.55  0.4   0     0.76
e3       0.55  0.36  0.37  0.37  0.55  0.36  0.37  0.37  0.55  0.37  0.35  0.35  0.55  0.35  0.36  0.38  0.55  0.4   0.4   0
```

As you can tell by the pairwise distances, the scores are about the same for Levenshtein as for Eventual, but the Jaccard scores are worse. This is because Raft is eliminating forked versions and preventing them from propagating, meaning that the originating nodes have more entries in their logs than they otherwise would (we need a mechanism to stop branches from propagating). Note, however that the Raft nodes are all identical. 

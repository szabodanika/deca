# DECA

Source code for Distributed Embodied Conversational Agents system.

### Usage

1. Install requirements with pip: `pip install -r requirements.txt`
2. Navigate to runner script directory `cd ./runner/`
3. Run simple running script to observe output with `python ./few_nodes.py`
4. Run scalable running script to observe behaviour under load with `python ./many_nodes.py`
5. Use <kbd>Ctrl</kbd> + C to stop

You can modify the runner scripts to start nodes with different parameters and on different scales. Search for
`SIMULATED USER BEHAVIOUR` in the source code to find the two places where you can programme embodiment node and conversational
agent node behaviour in absance of actual user input.


## Paper

Work in Progress, link soon

### Authors

Dániel Szabó, Achira Hendalage\
University of Oulu\
firstname.lastname@oulu.fi
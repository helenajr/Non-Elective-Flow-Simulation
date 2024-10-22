# Non-Elective-Flow-Simulation

### Problem: 
Poor patient flow is leading to long waits for admission in ED. This leads to poor performance against all the key ED wait metrics for the hospital and more importantly, there is evidence that long waits for admission in ED are associated with poorer outcomes for patients.
### Management strategies: 
The two main strategies employed to tackle this problem is increasing the number of beds (by creation of escalation beds) and trying to decrease discharge delays (reducing length of stay). Additionally we have a Same Day Emergency Care (SDEC) facility and it is unclear how the number of people admitted through this facility impacts the waits of those in ED.
### Key questions:
* Given x beds, how far does admitted length of stay have to reduce to meet particular waiting time targets for those queuing in ED? (Evidence based target)
* If we open 15 beds but keep admitted length of stay the same, what is the impact on ED waiting times and the various targets? (Evidence for a particular management strategy)
* What is the optimum number of people to stream from ED to SDEC to minimise ED waits? (Evidence for a particular management strategy)
### Outputs:
I plan to create DES model(s), using the methods taught on the HSMA, that are able to provide evidence for the questions above. I would  also hope to create a friendly user interface that my stakeholders could use to try out scenarios and help understand how the model works.

# Structure of the repo

### model_script
Contains both the model and code in one script to generate the outputs to make it easy to test the impact of changes and play around with outputs.

## app
This folder contains the code required to run the model as an app (with model classes and outputs separated into separate scripts), run app.py to run the app. On main branch the model code for the app and in model_script should always be the same.

## environment
The environment required to run the model / app.

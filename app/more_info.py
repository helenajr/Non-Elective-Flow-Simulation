import streamlit as st

st.title("More Information")

st.markdown("""
##### Conceptual model

Long admission delays in ED are primarily driven by waits for an available bed.
Reduced to its simplest possible components non-elective flow can be modelled
as below:
""")

st.image("img/model_diagram.png")

st.markdown("""
The inputs to the model are the number of patients needing non-elective 
admission. They can be admitted to a bed via ED, SDEC or directly. They must
wait in ED until a bed comes available. They remain in that bed for a period of
time until they are discharged. Some patients, who needed admission will depart
directly from ED, as they have completed thier whole treatment pathway while
queuing for a bed.
            
In the system described above there are 3 things that affect ED admission delays:
            
* Number of beds
* Number of people requiring admission
* How long people stay in a bed
            
Although the details of management strategies aimed at reducing admission delays
differ, they will need to have an effect on one or more of these things to
be effective.
            
This tool enables you to try out different scenarios to estimate the effect any
strategy will have on ED admission delays.
            
##### Computer model

The above conceptual model is represented inside the computer as a 'Discrete
Event Simulation'. The computer generates synthetic patients (just like in a
video game) and sends them through the system. The simulated patients will wait
in ED until a bed comes available, then they will stay in that bed for a period
of time and the timepoints when they move from one place to another are recorded
, just like in the real system. 
            
In the real system there is random variation in how frequently patients arrive 
and how long they stay in a bed and this is mirrored in the simulated system. 
The simulation runs for 10 * 60 day periods and then shows admission delay metrics
for that period, alongside confidence intervals. The number of runs can be 
increased by the user from 10 to 200 for greater confidence (but the model will
take longer to run).
            
##### How confident are we in the model results?
            
At the moment the model is in the early stages of development and has undergone
only very limited validation - at the moment use results with extreme caution.

"""
)
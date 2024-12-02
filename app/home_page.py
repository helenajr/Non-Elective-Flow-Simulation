import streamlit as st

st.title("Non-Elective Flow Simulation App")

st.markdown("""
Welcome to the Non-Elective Flow Simulation App (v0.0). The app and
underlying model are being developed by the Data & Analytics team
at the Countess of Chester Hospital. This app is designed to help understand 
the effect of different management strategies on ED admission delays (DTA waits)
. Please note that development of this tool is at an early stage and treat 
results with caution. We welcome any feedback on the tool.
""")

st.write("Head to the 'Run Simulation' page to get started.")

st.markdown("""
            
##### Example questions the model can provide evidence for:
* Given x beds, how far does admitted length of stay have to reduce to meet 
particular waiting time targets for those queuing in ED? (Evidence based target)
* If we open 15 beds but keep admitted length of stay the same, what is the 
impact on ED waiting times and the various targets? (Evidence for a particular 
management strategy)
* What is the optimum number of people to stream from ED to SDEC to minimise ED
waits for admission? (Evidence for a particular management strategy)

""")

st.markdown("""
##### Model diagram

The model simulates the system as illustrated in the flowchart below. For more
detail on how the model works see the 'More Information' page
""")

st.image("img/model_diagram.png")


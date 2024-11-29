import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

from des_classes1 import g, Trial

#Initialise session state
if 'button_click_count' not in st.session_state:
  st.session_state.button_click_count = 0
if 'session_results' not in st.session_state:
    st.session_state['session_results'] = []
if 'session_inputs' not in st.session_state:
    st.session_state['session_inputs'] = []

st.title("Non-Elective Flow Simulation")

with st.sidebar:
    mean_los_slider = st.slider("Adjust the mean los in hours",
                                min_value=100, max_value=300, value=225)
    num_nelbeds_slider = st.slider("Adjust the number of beds available",
                                min_value=300, max_value=500, value=434)
    daily_ed_adm_slider = st.slider("Adjust the average number of admissions via ED per day",
                                    min_value=20, max_value=100, value=38)
    daily_sdec_adm_slider = st.slider("Adjust the average number of admissions via SDEC per day",
                                    min_value=0, max_value=100, value=11)
    daily_other_adm_slider = st.slider("Adjust the average number of admissions via other routes per day",
                                    min_value=0, max_value=50, value=4)
    num_runs_slider = st. slider("Adjust the number of runs the model does",
                                 min_value=10, max_value=100, value=10)

g.mean_time_in_bed = (mean_los_slider * 60)
g.number_of_nelbeds = num_nelbeds_slider
g.ed_inter_visit = 1440/daily_ed_adm_slider
g.sdec_inter_visit = 1440/daily_sdec_adm_slider
g.other_inter_visit = 1440/daily_other_adm_slider
g.number_of_runs = num_runs_slider

tab1, tab2 = st.tabs(["Run the model", "Compare scenarios"])


with tab1:

    button_run_pressed = st.button("Run simulation")

    if button_run_pressed:
        with st.spinner("Simulating the system"):
            df_trial_results, all_results_patient_level, trial_summary = Trial().run_trial()
            
            # Adding to session state objects so we can compare scenarios
            
            # Comparing inputs
            st.session_state.button_click_count += 1
            col_name = f"Scenario {st.session_state.button_click_count}"
            # make dataframe with inputs, set an index, select as a series
            inputs_for_state = pd.DataFrame({
            'Input': ['Mean LoS', 'Number of beds', 'Admissions via ED', 
                'Admissions via SDEC', 'Admissions via Other', 'Number of runs'],
            col_name: [mean_los_slider, num_nelbeds_slider, daily_ed_adm_slider, 
                daily_sdec_adm_slider, daily_other_adm_slider, num_runs_slider]
            }).set_index('Input')[col_name]
            # Append input series to the session state
            st.session_state['session_inputs'].append(inputs_for_state)
            
            # Comparing results
            results_for_state = trial_summary['Mean']
            results_for_state.name = col_name
            st.session_state['session_results'].append(results_for_state)
        
            ################
            st.write(f"You've run {st.session_state.button_click_count} scenarios")
            st.write("These metrics are for a 60 day period and only include those patients actually admitted")

            st.dataframe(trial_summary)
            ###################

            #Convert wait times into hours
            all_results_patient_level['q_time_bed_hours'] = all_results_patient_level['Q Time Bed'] / 60.0
            all_results_patient_level['under4hrflag'] = np.where(all_results_patient_level['q_time_bed_hours'] < 4, 1, 0)
            all_results_patient_level['dta12hrflag'] = np.where(all_results_patient_level['q_time_bed_hours'] > 12, 1, 0)
            all_results_patient_level['q_time_bed_or_renege'] = all_results_patient_level['Q Time Bed|Renege'] / 60.0
            
            #value = trial_summary.loc["Mean Q Time (Hrs)", "Mean"]
            #label = f'Mean Q Time: {round(trial_summary.loc["Mean Q Time (Hrs)", "Mean"])} hrs'
            
            #Create the histogram
            fig = plt.figure(figsize=(8, 6))
            sns.histplot(
            all_results_patient_level['q_time_bed_hours'], 
            bins=range(int(all_results_patient_level['q_time_bed_hours'].min()), 
                    int(all_results_patient_level['q_time_bed_hours'].max()) + 1, 1), 
            kde=False

            # # Set the boundary for the bins to start at 0
            plt.xlim(left=0)

            # Add vertical lines with labels
            lines = [
                {"x": trial_summary.loc["Mean Q Time (Hrs)", "Mean"], "color": "tomato", "label": f'Mean Q Time: {round(trial_summary.loc["Mean Q Time (Hrs)", "Mean"])} hrs'},
                {"x": 4, "color": "mediumturquoise", "label": f'4 Hr DTA Performance: {round(trial_summary.loc["4hr DTA Performance (%)", "Mean"])}%'},
                {"x": 12, "color": "royalblue", "label": f'12 Hr DTAs per day: {round(trial_summary.loc["12hr DTAs", "Mean"])} hrs'},
                {"x": trial_summary.loc["95th Percentile Q", "Mean"], "color": "goldenrod", "label": f'95th Percentile Q Time: {round(trial_summary.loc["95th Percentile Q", "Mean"])} hrs'},
                {"x": trial_summary.loc["Max Q Time (Hrs)", "Mean"], "color": "slategrey", "label": f'Max Q Time: {round(trial_summary.loc["Max Q Time (Hrs)", "Mean"])} hrs'},
            ]

            for line in lines:
                # Add the vertical line
                plt.axvline(x=line["x"], color=line["color"], linestyle='--', linewidth=1, zorder=0)
                
                # Add label with text
                plt.text(line["x"] + 2, plt.ylim()[1] * 0.95, line["label"], 
                        color=line["color"], ha='left', va='top', fontsize=10, rotation=90,
                        bbox=dict(facecolor='white', edgecolor='none', alpha=0.3, boxstyle='round,pad=0.5'))

            # Add transparent rectangles for confidence intervals
            ci_ranges = [
                {"lower": trial_summary.loc["Mean Q Time (Hrs)", "Lower 95% CI"], 
                "upper": trial_summary.loc["Mean Q Time (Hrs)", "Upper 95% CI"], "color": "tomato"},
                {"lower": trial_summary.loc["95th Percentile Q", "Lower 95% CI"], 
                "upper": trial_summary.loc["95th Percentile Q", "Upper 95% CI"], "color": "goldenrod"},
                {"lower": trial_summary.loc["Max Q Time (Hrs)", "Lower 95% CI"], 
                "upper": trial_summary.loc["Max Q Time (Hrs)", "Upper 95% CI"], "color": "slategrey"},
            ]

            for ci in ci_ranges:

                plt.axvspan(
                    ci["lower"],
                    ci["upper"],
                    color=ci["color"],
                    alpha=0.2,
                    zorder=0

            # Add labels and title if necessary
            plt.xlabel('Admission Delays (Hours)')
            plt.title('Histogram of Admission Delays (All Runs)')
            fig.text(0.8, 0.01, 'Boxes show 95% CI.', ha='center', fontsize=10)

            # Display the plot
            st.pyplot(fig)
            # ###################
        
with tab2:
    st.write(f"You've run {st.session_state.button_click_count} scenarios")

    # Convert series back to df, transpose, display
    if st.session_state.button_click_count > 0:
        st.write("Here are your inputs for each scenario")
        current_i_df = pd.DataFrame(st.session_state['session_inputs']).T
        st.dataframe(current_i_df)
        
        st.write("Here are your results for each scenario")
        current_state_df = pd.DataFrame(st.session_state['session_results']).T
        st.dataframe(current_state_df)
import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

from des_classes1 import g, Trial

st.title("Non-Elective Flow Simulation")

with st.sidebar:
    mean_los_slider = st.slider("Adjust the mean los in hours",
                                min_value=100, max_value=300, value=225)
    num_nelbeds_slider = st.slider("Adjust the number of beds available",
                                min_value=300, max_value=500, value=434)

g.mean_time_in_bed = (mean_los_slider * 60)
g.number_of_nelbeds = num_nelbeds_slider

button_run_pressed = st.button("Run simulation")

if button_run_pressed:
    with st.spinner("Simulating the system"):
        df_trial_results, all_results_patient_level, means_over_trial = Trial().run_trial()

        all_results_patient_level['q_time_bed_hours'] = all_results_patient_level['Q Time Bed'] / 60.0
        all_results_patient_level['under4hrflag'] = np.where(all_results_patient_level['q_time_bed_hours'] < 4, 1, 0)
        all_results_patient_level['dta12hrflag'] = np.where(all_results_patient_level['q_time_bed_hours'] > 12, 1, 0)
        all_results_patient_level['q_time_bed_or_renege'] = all_results_patient_level['Q Time Bed|Renege'] / 60.0

        ################
        st.write("These metrics only include those patients actually admitted")
        #calculating the metrics
        #Mean
        mean_pat_data = round(all_results_patient_level['q_time_bed_hours'].mean())

        #Min
        min_pat_data = round(all_results_patient_level['q_time_bed_hours'].min())

        #Max
        max_pat_data = round(all_results_patient_level['q_time_bed_hours'].max())

        #95th percentile
        q_pat_data = round(all_results_patient_level['q_time_bed_hours'].quantile(0.95))

        #4hr performance
        perf4hr_pat_data = "{:.0%}".format(all_results_patient_level['under4hrflag'].mean())

        #12hr DTAs per day
        dtasperday = round((all_results_patient_level['dta12hrflag'].sum() / g.number_of_runs) / 60.0)

        #Patients reneged from ED
        reneged = round(all_results_patient_level['reneged'].sum() / g.number_of_runs)

        st.write(f"Mean Q Time for admission in ED is {mean_pat_data}")
        
        data = {
            "Metric": ["Mean Q Time (Hrs)", "Min Q Time", "Max Q Time (Hrs)", "4hr (DTA) Performance",
                        "12hr DTAs per day", "95th Percentile Q Time (Hrs)", "Reneged"],
            "Results": [mean_pat_data, min_pat_data, max_pat_data, perf4hr_pat_data, 
                        dtasperday, q_pat_data, reneged]
        }

        st.dataframe(data)

        ###################
        # Create the histogram
        fig = plt.figure(figsize=(8, 6))
        sns.histplot(all_results_patient_level['q_time_bed_hours'], bins=range(int(all_results_patient_level['q_time_bed_hours'].min()), 
                                                            int(all_results_patient_level['q_time_bed_hours'].max()) + 1, 1), 
                    kde=False)

        # Set the boundary for the bins to start at 0
        plt.xlim(left=0)

        # Add vertical lines
        plt.axvline(x=mean_pat_data, color='tomato', linestyle='--', linewidth=1, label='Mean Q Time', zorder=0)
        plt.axvline(x=4, color='mediumturquoise', linestyle='--', linewidth=1, label='4 Hours', zorder=0)
        plt.axvline(x=12, color='royalblue', linestyle='--', linewidth=1, label='12 Hours', zorder=0)
        plt.axvline(x=q_pat_data, color='goldenrod', linestyle='--', linewidth=1, zorder=0)
        plt.axvline(x=max_pat_data, color='slategrey', linestyle='--', linewidth=1, zorder=0)

        # Add labels to the lines
        plt.text(mean_pat_data + 2, plt.ylim()[1] * 0.95, f'Mean Q Time: {mean_pat_data} hrs', color='tomato', ha='left', va='top', fontsize=10, rotation=90,
                    bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, boxstyle='round,pad=0.5'))
        plt.text(4 + 2, plt.ylim()[1] * 0.95, f'4 Hr Performance: {perf4hr_pat_data}', color='mediumturquoise', ha='left', va='top', fontsize=10, rotation=90,
                    bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, boxstyle='round,pad=0.5'))
        plt.text(12 + 2, plt.ylim()[1] * 0.95, f'12 Hr DTAs per day: {dtasperday}', color='royalblue', ha='left', va='top', fontsize=10, rotation=90,
                    bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, boxstyle='round,pad=0.5'))
        plt.text(q_pat_data + 2, plt.ylim()[1] * 0.95, f'95th Percentile Q Time: {q_pat_data} hrs', color='goldenrod', ha='left', va='top', fontsize=10, rotation=90,
                    bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, boxstyle='round,pad=0.5'))
        plt.text(max_pat_data + 1, plt.ylim()[1] * 0.95, f'Max Q Time: {max_pat_data} hrs', color='slategrey', ha='left', va='top', fontsize=10, rotation=90)

        # Add labels and title if necessary
        plt.xlabel('Admission Delays (Hours)')
        plt.ylabel('Frequency')
        plt.title('Histogram of Admission Delays')

        # Display the plot
        st.pyplot(fig)
        ###################

        st.dataframe(all_results_patient_level)

    #data0 = pd.DataFrame(data)

    #st.dataframe(data0)
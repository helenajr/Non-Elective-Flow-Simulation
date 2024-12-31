import pandas as pd
import numpy as np
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt
from app.des_classes1 import g, Trial

#overwrite g class - so its easy to play around with
g.ed_inter_visit = (1440 / 38) # convert daily arrivals into inter-arrival time
g.sdec_inter_visit = (1440 / 11)
g.other_inter_visit = (1440 / 4)
g.number_of_nelbeds = 434
g.mean_time_in_bed = (225 * 60) # convert hrs to minutes
g.sd_time_in_bed = (405 * 60) # convert hrs to minutes
g.sim_duration = (60 * 24 * 60) # convert days into minutes
g.warm_up_period = (60 * 24 * 60)
g.number_of_runs = 10

# Call the run_trial method of our Trial object
df_trial_results, all_results_patient_level, trial_summary = Trial().run_trial()

# These are the 3 current outputs from running a trial
display(df_trial_results.head(100))
display(all_results_patient_level.head(100))
display(trial_summary.head(100))

###################HISTOGRAM###########################################################

#Convert wait times into hours
all_results_patient_level['q_time_bed_hours'] = all_results_patient_level['Q Time Bed'] / 60.0
all_results_patient_level['under4hrflag'] = np.where(all_results_patient_level['q_time_bed_hours'] < 4, 1, 0)
all_results_patient_level['dta12hrflag'] = np.where(all_results_patient_level['q_time_bed_hours'] > 12, 1, 0)
all_results_patient_level['q_time_bed_or_renege'] = all_results_patient_level['Q Time Bed|Renege'] / 60.0

#Create the histogram
fig = plt.figure(figsize=(8, 6))
sns.histplot(
all_results_patient_level['q_time_bed_hours'], 
bins=range(int(all_results_patient_level['q_time_bed_hours'].min()), 
        int(all_results_patient_level['q_time_bed_hours'].max()) + 1, 1), 
kde=False)

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
        zorder=0)

# Add labels and title if necessary
plt.xlabel('Admission Delays (Hours)')
plt.title('Histogram of Admission Delays (All Runs)')
fig.text(0.8, 0.01, 'Boxes show 95% CI.', ha='center', fontsize=10)

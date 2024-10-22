print("Importing libraries")

import simpy
import random
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import time
import Lognormal # (from a .py file, written by Tom Monks)

# Class to store global parameter values.
class g:
    ed_inter_visit = 37.7 # see observed_edintervist notebook
    sdec_inter_visit = 128.8 # see sdec intervisit notebook
    other_inter_visit = 375.7 # see other intervisit notebook.
    number_of_nelbeds = 434 # see number beds notebook
    mean_time_in_bed = 13522 # see mean los notebook
    sd_time_in_bed = 24297
    sim_duration = 86400 #run for 60 days
    warm_up_period = 86400 # warm up for 60 days - need to test if  this is long enough
    number_of_runs = 10

# Class representing patients needing admission.
class Patient:
    def __init__(self, p_id):
        self.id = p_id
        self.q_time_bed = 0
        self.start_q_bed = 0
        self.end_q_bed = 0
        self.renege_time = random.randint(0, 9000) #random.randint(0, 9000) # some amount of time between 24hrs and 150hrs
        self.priority = random.randint(1,2)
        self.priority_update = random.randint(0, 9000)
        self.sdec_other_priority = 0.8

# Class representing our model of the hospital.
class Model:
    # Constructor to set up the model for a run.  We pass in a run number when
    # we create a new model.
    def __init__(self, run_number):
        # Create a SimPy environment in which everything will live
        self.env = simpy.Environment()

        # Create a patient counter (which we'll use as a patient ID)
        self.patient_counter = 0

        # Create our resources
        self.nelbed = simpy.PriorityResource(
            self.env, capacity=g.number_of_nelbeds)

        # Store the passed in run number
        self.run_number = run_number

        # Create a new DataFrame that will store results against patientID
        self.results_df = pd.DataFrame()
        self.results_df["Patient ID"] = [1]
        self.results_df["InitialPriority"] = [0.0]
        self.results_df["UpdatedPriority"] = [0.0]
        self.results_df["Q Time Bed"] = [0.0]
        self.results_df["Q Time Bed|Renege"] = [0.0]
        self.results_df["dta"] = [0]
        self.results_df["checkout"] = [0]
        self.results_df["Q Time Bed SDEC"] = [0.0]
        self.results_df["sdec_dta"] = [0]
        self.results_df["sdec_checkout"] = [0]
        self.results_df["Q Time Bed Other"] = [0.0]
        self.results_df["other_dta"] = [0]
        self.results_df["other_checkout"] = [0]
        self.results_df["reneged"] = [0]
        self.results_df.set_index("Patient ID", inplace=True)

        # Create an attribute to store the mean queuing times
        self.mean_q_time_bed = 0
    
    # A generator function for ed patient arrivals
    def generator_patient_arrivals(self):
        # We use an infinite loop here to keep doing this indefinitely
        while True:
            # Increment the patient counter by 1 (this means our first patient
            # will have an ID of 1)
            self.patient_counter += 1
            
            # Create a new patient - an instance of the Patient Class we
            # defined above. We pass the patient counter to use as the ID.
            p = Patient(self.patient_counter)

            # Tell SimPy to start up the attend_hospital function with
            # this patient
            self.env.process(self.attend_hospital(p))

            # Randomly sample the time to the next patient arriving.
            sampled_inter = random.expovariate(1.0 / g.ed_inter_visit)

            # Freeze until the inter-arrival time we sampled above has elapsed.  
            yield self.env.timeout(sampled_inter)
    
    def generator_sdec_arrivals(self):
        while True:
            self.patient_counter += 1
            
            p = Patient(self.patient_counter)

            self.env.process(self.attend_sdec(p))

            sampled_inter = random.expovariate(1.0 / g.sdec_inter_visit)

            yield self.env.timeout(sampled_inter)

    def generator_other_arrivals(self):
        while True:
            self.patient_counter += 1
            
            p = Patient(self.patient_counter)

            self.env.process(self.attend_other(p))

            sampled_inter = random.expovariate(1.0 / g.other_inter_visit)

            yield self.env.timeout(sampled_inter)

    def attend_hospital(self, patient):

        # Record the time the patient started queuing for a bed and their initial priority
        # If we are through the warm up period
        start_q_bed = self.env.now
        patient.start_q_bed = start_q_bed - g.warm_up_period

        if start_q_bed > g.warm_up_period:
            self.results_df.at[patient.id, "dta"] = (
                            patient.start_q_bed
                        )
            self.results_df.at[patient.id, "InitialPriority"] = (
                            patient.priority
                        )
        
        # Request a bed
        with self.nelbed.request(priority=patient.priority) as req:
            # Freeze the function until one of 3 things happens....
            result_of_queue = (yield req | # they get a bed
                               self.env.timeout(patient.renege_time) | # they improve
                               self.env.timeout(patient.priority_update)) # they deteriorate

            # if the result is they get a bed, record the relevant details
            if req in result_of_queue:
                end_q_bed = self.env.now
                patient.end_q_bed = end_q_bed - g.warm_up_period

                # Calculate the time this patient was queuing for the bed
                patient.q_time_bed = end_q_bed - start_q_bed

                # Only if we are through the warm up period, store the details
                # next to the appropriate patientid (.at accesses a particular cell)
                if start_q_bed > g.warm_up_period:
                    self.results_df.at[patient.id, "Q Time Bed"] = (
                        patient.q_time_bed
                    )
                    self.results_df.at[patient.id, "Q Time Bed|Renege"] = (
                        patient.q_time_bed
                    )
                    self.results_df.at[patient.id, "checkout"] = (
                        patient.end_q_bed
                    )
                    self.results_df.at[patient.id, "reneged"] = 0
                
                sampled_bed_time = Lognormal.Lognormal(
                    g.mean_time_in_bed, g.sd_time_in_bed).sample()
                
                # Freeze this function in place for the activity time we sampled
                # above.  This is the patient spending time in the bed.
                yield self.env.timeout(sampled_bed_time)
            # If the result of the queue was deterioration    
            elif patient.priority_update < patient.renege_time:
                # Update their priority
                patient.priority = patient.priority - 2.2
                # Make another bed request with new priority
                with self.nelbed.request(priority=patient.priority) as req:
                    yield req
                    end_q_bed = self.env.now
                    patient.end_q_bed = end_q_bed - g.warm_up_period
                    patient.q_time_bed = end_q_bed - start_q_bed

                    if start_q_bed > g.warm_up_period:
                        self.results_df.at[patient.id, "Q Time Bed"] = (
                            patient.q_time_bed
                        )
                        self.results_df.at[patient.id, "checkout"] = (
                            patient.end_q_bed
                        )
                        self.results_df.at[patient.id, "reneged"] = 0
                        self.results_df.at[patient.id, "UpdatedPriority"] = (
                            patient.priority
                        )
                
                    sampled_bed_time = Lognormal.Lognormal(
                        g.mean_time_in_bed, g.sd_time_in_bed).sample()
                
                    yield self.env.timeout(sampled_bed_time)
            # If patient improves enough to leave the queue
            else:
                end_q_bed = self.env.now
                patient.end_q_bed = end_q_bed - g.warm_up_period
                patient.q_time_bed = end_q_bed - start_q_bed

                if start_q_bed > g.warm_up_period:
                    self.results_df.at[patient.id, "reneged"] = 1
                    self.results_df.at[patient.id, "Q Time Bed|Renege"] = (
                        patient.q_time_bed
                    )
                    self.results_df.at[patient.id, "checkout"] = (
                            patient.end_q_bed
                    )
    
    def attend_sdec(self, patient):

        start_q_bed = self.env.now
        patient.start_q_bed = start_q_bed - g.warm_up_period

        with self.nelbed.request(priority=patient.sdec_other_priority) as req:
            yield req

            end_q_bed = self.env.now
            patient.end_q_bed = end_q_bed - g.warm_up_period

            patient.q_time_bed = end_q_bed - start_q_bed

            if start_q_bed > g.warm_up_period:
                self.results_df.at[patient.id, "Q Time Bed SDEC"] = (
                    patient.q_time_bed
                )
                self.results_df.at[patient.id, "sdec_dta"] = (
                    patient.start_q_bed
                )
                self.results_df.at[patient.id, "sdec_checkout"] = (
                    patient.end_q_bed
                )
            
            sampled_bed_time = random.expovariate(1.0 / 
                                                        g.mean_time_in_bed)
            
            yield self.env.timeout(sampled_bed_time)

    def attend_other(self, patient):

        start_q_bed = self.env.now
        patient.start_q_bed = start_q_bed - g.warm_up_period

        with self.nelbed.request(priority=patient.sdec_other_priority) as req:
            yield req

            end_q_bed = self.env.now
            patient.end_q_bed = end_q_bed - g.warm_up_period

            patient.q_time_bed = end_q_bed - start_q_bed

            if start_q_bed > g.warm_up_period:
                self.results_df.at[patient.id, "Q Time Bed Other"] = (
                    patient.q_time_bed
                )
                self.results_df.at[patient.id, "other_dta"] = (
                    patient.start_q_bed
                )
                self.results_df.at[patient.id, "other_checkout"] = (
                    patient.end_q_bed
                )
            
            sampled_bed_time = random.expovariate(1.0 / 
                                                        g.mean_time_in_bed)
            
            yield self.env.timeout(sampled_bed_time)

    # This method calculates results over a single run.
    def calculate_run_results(self):
        #drop the dummy patient we entered when we set up the df
        self.results_df.drop([1], inplace=True)
        # Take the mean of the queuing times across patients in this run of the 
        # model.
        self.mean_q_time_bed = self.results_df["Q Time Bed"].mean()

    # The run method starts up the DES entity generators, runs the simulation,
    # and in turns calls anything we need to generate results for the run
    def run(self):
        # Start up our DES entity generators that create new patients. 
        self.env.process(self.generator_patient_arrivals())
        self.env.process(self.generator_sdec_arrivals())
        self.env.process(self.generator_other_arrivals())

        # Run the model for the duration specified in g class
        self.env.run(until=(g.sim_duration + g.warm_up_period))

        # Now the simulation run has finished, call the method that calculates
        # run results
        self.calculate_run_results()

        # Return patient level results for this run
        return (self.results_df)

# Class representing a Trial for our simulation - a batch of simulation runs.
class Trial:
    # The constructor sets up a pandas dataframe that will store the key
    # results from each run against run number, with run number as the index.
    def  __init__(self):
        self.df_trial_results = pd.DataFrame()
        self.df_trial_results["Run Number"] = [0]
        self.df_trial_results["Mean Q Time Bed"] = [0.0]
        self.df_trial_results.set_index("Run Number", inplace=True)

    # Method to calculate and store overall means.
    def calculate_means_over_trial(self):
        self.mean_q_time_trial = (
            self.df_trial_results["Mean Q Time Bed"].mean()
        )

    # Method to print out the results from the trial.
    # def print_trial_results(self):
    #     print ("Trial Results")
    #     print (self.df_trial_results)

    # def print_alltrial_summary(self):
    #     print("Mean Q Time Bed")
    #     print(self.df_trial_results["Mean Q Time Bed"].mean())

    # Method to run a trial
    def run_trial(self):
        # Run the simulation for the number of runs specified in g class.
        # For each run, we create a new instance of the Model class and call its
        # run method, which sets everything else in motion.
        results_dfs = []
        
        for run in range(g.number_of_runs):
            my_model = Model(run)
            patient_level_results = my_model.run()
            
            self.df_trial_results.loc[run] = [my_model.mean_q_time_bed]

            patient_level_results = patient_level_results.round(2)
            patient_level_results['run'] = run

            results_dfs.append(patient_level_results)
        
        #stick all the individual results together
        all_results_patient_level = pd.concat(results_dfs)
                                              
        # Once the trial (ie all runs) has completed, print the final results
        #self.print_trial_results()
        #self.print_alltrial_summary()

        self.calculate_means_over_trial()

        return self.df_trial_results, all_results_patient_level, self.mean_q_time_trial

# Create an instance of the Trial class
my_trial = Trial()

print(f"Running {g.number_of_runs} simulations......")
start_time = time.time()

# Call the run_trial method of our Trial object
df_trial_results, all_results_patient_level, means_over_trial =  my_trial.run_trial()


end_time = time.time()
elapsed_time = end_time - start_time
print(f"That took {round(elapsed_time)} seconds")
print("Doing some transformations")

#Convert wait times into hours
all_results_patient_level['q_time_bed_hours'] = all_results_patient_level['Q Time Bed'] / 60.0
all_results_patient_level['under4hrflag'] = np.where(all_results_patient_level['q_time_bed_hours'] < 4, 1, 0)
all_results_patient_level['dta12hrflag'] = np.where(all_results_patient_level['q_time_bed_hours'] > 12, 1, 0)
all_results_patient_level['q_time_bed_or_renege'] = all_results_patient_level['Q Time Bed|Renege'] / 60.0

################
print("Calculating wait time metrics.....")
print("These metrics only include those patients actually admitted")
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

#save these in a df
# according to chat you want to make it into a dictionary first
data = {
    "Metric": ["Mean Q Time (Hrs)", "Min Q Time", "Max Q Time (Hrs)", "4hr (DTA) Performance",
                "12hr DTAs per day", "95th Percentile Q Time (Hrs)", "Reneged"],
    "Results": [mean_pat_data, min_pat_data, max_pat_data, perf4hr_pat_data, 
                dtasperday, q_pat_data, reneged]
}

df = pd.DataFrame(data)

display(df)

#####################
#plotting and showing a single figure

# Create the histogram
plt.figure(figsize=(8, 6))
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
plt.show()

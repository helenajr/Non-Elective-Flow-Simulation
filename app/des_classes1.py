
import simpy
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time
from sim_tools.distributions import (Exponential, Lognormal, Uniform)
import scipy.stats as stats
from vidigi.utils import populate_store

class g: # global
    ed_inter_visit = 37.7 # see observed_edintervist notebook
    sdec_inter_visit = 128.8 # see sdec intervisit notebook
    other_inter_visit = 375.7 # see other intervisit notebook.
    number_of_nelbeds = 434 # see number beds notebook
    mean_time_in_bed = 13500 # see mean los notebook
    sd_time_in_bed = 24297
    sim_duration = 86400 #run for 60 days
    warm_up_period = 86400 # warm up for 60 days - need to test if  this is long enough
    number_of_runs = 10

class Patient:
    def __init__(self, p_id):
        self.id = p_id
        self.department = ""
        self.q_time_bed = 0
        self.start_q_bed = 0
        self.end_q_bed = 0
        self.renege_time = 0
        self.priority = 0
        self.priority_update = 0
        self.sdec_other_priority = 0.8

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
        self.results_df["Department"] = [""]
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
        self.ed_admissions = 0
        self.mean_q_time_bed = 0
        self.sdec_admissions = 0
        self.mean_q_time_sdec = 0
        self.other_admissions = 0
        self.mean_q_time_other = 0
        self.reneged = 0

        # Initialise distributions for generators
        self.ed_inter_visit_dist = Exponential(mean = g.ed_inter_visit, random_seed = self.run_number*2)
        self.sdec_inter_visit_dist = Exponential(mean = g.sdec_inter_visit, random_seed = self.run_number*3)
        self.other_inter_visit_dist = Exponential(mean = g.other_inter_visit, random_seed = self.run_number*4)
        self.mean_time_in_bed_dist = Lognormal(g.mean_time_in_bed, g.sd_time_in_bed, random_seed = self.run_number*5)
        self.renege_time = Uniform(0, 9000, random_seed = self.run_number*6)
        self.priority_update = Uniform(0, 9000, random_seed = self.run_number*7)
        self.priority = Uniform(1,2, random_seed = self.run_number*8)
    
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
            p.department = "ED"
            p.renege_time = self.renege_time.sample()
            p.priority = round(self.priority.sample())
            p.priority_update = self.priority_update.sample()

            # Tell SimPy to start up the attend_hospital function with
            # this patient
            self.env.process(self.attend_hospital(p))

            # Randomly sample the time to the next patient arriving.
            sampled_inter = self.ed_inter_visit_dist.sample()

            # Freeze until the inter-arrival time we sampled above has elapsed.  
            yield self.env.timeout(sampled_inter)
    
    def generator_sdec_arrivals(self):
        while True:
            self.patient_counter += 1
            
            p = Patient(self.patient_counter)
            p.department = "SDEC"

            self.env.process(self.attend_sdec(p))

            sampled_inter = self.sdec_inter_visit_dist.sample()

            yield self.env.timeout(sampled_inter)

    def generator_other_arrivals(self):
        while True:
            self.patient_counter += 1
            
            p = Patient(self.patient_counter)
            p.department = "Other"

            self.env.process(self.attend_other(p))

            sampled_inter = self.other_inter_visit_dist.sample()

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
            self.results_df.at[patient.id, "Department"] = (
                            patient.department
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
                
                sampled_bed_time = self.mean_time_in_bed_dist.sample()
                
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
                
                    sampled_bed_time = self.mean_time_in_bed_dist.sample()
                
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
                self.results_df.at[patient.id, "Department"] = (
                            patient.department
                        )
            
            sampled_bed_time = self.mean_time_in_bed_dist.sample()
            
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
                self.results_df.at[patient.id, "Department"] = (
                            patient.department
                        )
            
            sampled_bed_time = self.mean_time_in_bed_dist.sample()
            
            yield self.env.timeout(sampled_bed_time)

    # This method calculates results over a single run.
    def calculate_run_results(self):
        #drop the dummy patient we entered when we set up the df
        self.results_df.drop([1], inplace=True)
        # Take the mean of the queuing times across patients in this run of the 
        # model.
        self.ed_admissions = (self.results_df["Department"] == "ED").sum()
        self.mean_q_time_bed = (self.results_df["Q Time Bed"].mean()) / 60.0
        self.min_q_time_bed = (self.results_df["Q Time Bed"].min()) / 60.0
        self.max_q_time_bed = (self.results_df["Q Time Bed"].max()) / 60.0
        self.perf_4hr = ((self.results_df["Q Time Bed"] < 240).sum() / self.ed_admissions)
        self.dta_12hr = round((self.results_df["Q Time Bed"] > 720).sum() / 60.0) # is this correct?
        self.q_time_bed_95 = self.results_df["Q Time Bed"].quantile(0.95) / 60.0
        self.sdec_admissions = (self.results_df["Department"] == "SDEC").sum()
        self.mean_q_time_sdec = (self.results_df["Q Time Bed SDEC"].mean()) / 60.0
        self.other_admissions = (self.results_df["Department"] == "Other").sum()
        self.mean_q_time_other = (self.results_df["Q Time Bed Other"].mean()) / 60.0
        self.reneged = (self.results_df["reneged"]).sum()

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

    # Empty df that will store results from each run against run number.
    def  __init__(self):
        self.df_trial_results = pd.DataFrame()
        self.df_trial_results["Run Number"] = [0]
        self.df_trial_results["ED Admissions"] = [0]
        self.df_trial_results["Mean Q Time Bed"] = [0.0]
        self.df_trial_results["Min Q Time Bed"] = [0.0]
        self.df_trial_results["Max Q Time Bed"] = [0.0]
        self.df_trial_results["4hr (DTA) Performance"] = [0.0]
        self.df_trial_results["12hr DTAs"] = [0]
        self.df_trial_results["95th Percentile Q"] = [0.0]
        self.df_trial_results["SDEC Admissions"] = [0]
        self.df_trial_results["Mean Q Time SDEC"] = [0.0]
        self.df_trial_results["Other Admissions"] = [0]
        self.df_trial_results["Mean Q Time Other"] = [0.0]
        self.df_trial_results["Reneged"] = [0]
        self.df_trial_results.set_index("Run Number", inplace=True)

    def calculate_trial_summary(self): # calculate single summary stat across all runs
        #ED Admissions
        self.mean_admission = (
            self.df_trial_results["ED Admissions"].mean()
        )
        self.std_admission = (
            self.df_trial_results["ED Admissions"].std()
        )
        self.se_admission = self.std_admission / np.sqrt(g.number_of_runs)
        self.lowerci_admission, self.upperci_admission = (
            stats.norm.interval(0.95, loc=self.mean_admission, scale=self.se_admission)
        )
        self.min_admission = (
            self.df_trial_results["ED Admissions"].min()
        )
        self.max_admission = (
            self.df_trial_results["ED Admissions"].max()
        )
        #Mean Q Time
        self.mean_q_time_trial = (
            self.df_trial_results["Mean Q Time Bed"].mean()
        )
        self.std_mean_q_time_trial = (
            self.df_trial_results["Mean Q Time Bed"].std()
        )
        self.se_mean_q_time_trial = self.std_mean_q_time_trial / np.sqrt(g.number_of_runs)
        self.lowerci_mean_q_time_trial, self.upperci_mean_q_time_trial = (
            stats.norm.interval(0.95, loc=self.mean_q_time_trial, scale=self.se_mean_q_time_trial)
        )
        self.min_mean_q_time_trial = (
            self.df_trial_results["Mean Q Time Bed"].min()
        )
        self.max_mean_q_time_trial = (
            self.df_trial_results["Mean Q Time Bed"].max()
        )
        #Min Q Time
        self.mean_min = (
            self.df_trial_results["Min Q Time Bed"].mean()
        )
        self.std_min = (
            self.df_trial_results["Min Q Time Bed"].std()
        )
        self.se_min = self.std_min / np.sqrt(g.number_of_runs)
        self.lowerci_min, self.upperci_min = (
            stats.norm.interval(0.95, loc=self.mean_min, scale=self.se_min)
        )
        self.min_min = (
            self.df_trial_results["Min Q Time Bed"].min()
        )
        self.max_min = (
            self.df_trial_results["Min Q Time Bed"].max()
        )
        #Max Q Time
        self.mean_max = (
            self.df_trial_results["Max Q Time Bed"].mean()
        )
        self.std_max = (
            self.df_trial_results["Max Q Time Bed"].std()
        )
        self.se_max = self.std_max / np.sqrt(g.number_of_runs)
        self.lowerci_max, self.upperci_max = (
            stats.norm.interval(0.95, loc=self.mean_max, scale=self.se_max)
        )
        self.min_max = (
            self.df_trial_results["Max Q Time Bed"].min()
        )
        self.max_max = (
            self.df_trial_results["Max Q Time Bed"].max()
        )
        #4hr Performance
        self.mean_4hr = (
            self.df_trial_results["4hr (DTA) Performance"].mean()
        )
        self.std_4hr = (
            self.df_trial_results["4hr (DTA) Performance"].std()
        )
        self.se_4hr = self.std_4hr / np.sqrt(g.number_of_runs)
        self.lowerci_4hr, self.upperci_4hr = (
            stats.norm.interval(0.95, loc=self.mean_4hr, scale=self.se_4hr)
        )
        self.min_4hr = (
            self.df_trial_results["4hr (DTA) Performance"].min()
        )
        self.max_4hr = (
            self.df_trial_results["4hr (DTA) Performance"].max()
        )
        #12hr DTAs
        self.mean_12hr = (
            self.df_trial_results["12hr DTAs"].mean()
        )
        self.std_12hr = (
            self.df_trial_results["12hr DTAs"].std()
        )
        self.se_12hr = self.std_12hr / np.sqrt(g.number_of_runs)
        self.lowerci_12hr, self.upperci_12hr = (
            stats.norm.interval(0.95, loc=self.mean_12hr, scale=self.se_12hr)
        )
        self.min_12hr = (
            self.df_trial_results["12hr DTAs"].min()
        )
        self.max_12hr = (
            self.df_trial_results["12hr DTAs"].max()
        )
        #95th Percentile
        self.mean_95 = (
            self.df_trial_results["95th Percentile Q"].mean()
        )
        self.std_95 = (
            self.df_trial_results["95th Percentile Q"].std()
        )
        self.se_95 = self.std_95 / np.sqrt(g.number_of_runs)
        self.lowerci_95, self.upperci_95 = (
            stats.norm.interval(0.95, loc=self.mean_95, scale=self.se_95)
        )
        self.min_95 = (
            self.df_trial_results["95th Percentile Q"].min()
        )
        self.max_95 = (
            self.df_trial_results["95th Percentile Q"].max()
        )
        #SDEC Admissions
        self.mean_sdec = (
            self.df_trial_results["SDEC Admissions"].mean()
        )
        self.std_sdec = (
            self.df_trial_results["SDEC Admissions"].std()
        )
        self.se_sdec = self.std_sdec / np.sqrt(g.number_of_runs)
        self.lowerci_sdec, self.upperci_sdec = (
            stats.norm.interval(0.95, loc=self.mean_sdec, scale=self.se_sdec)
        )
        self.min_sdec = (
            self.df_trial_results["SDEC Admissions"].min()
        )
        self.max_sdec = (
            self.df_trial_results["SDEC Admissions"].max()
        )
        #Reneged
        self.mean_reneged = (
            self.df_trial_results["Reneged"].mean()
        )
        self.std_reneged = (
            self.df_trial_results["Reneged"].std()
        )
        self.se_reneged = self.std_reneged / np.sqrt(g.number_of_runs)
        self.lowerci_reneged, self.upperci_reneged = (
            stats.norm.interval(0.95, loc=self.mean_reneged, scale=self.se_reneged)
        )
        self.min_reneged = (
            self.df_trial_results["Reneged"].min()
        )
        self.max_reneged = (
            self.df_trial_results["Reneged"].max()
        )

        #pandas dataframe to hold the results
        self.trial_summary_df = pd.DataFrame()
        self.trial_summary_df["Metric"] = ["ED Admissions",
                                           "Mean Q Time (Hrs)", 
                                           "Min Q Time",
                                           "Max Q Time (Hrs)",
                                           "4hr (DTA) Performance",
                                           "12hr DTAs",
                                           "95th Percentile Q",
                                           "SDEC Admissions",
                                           "Reneged"]
        self.trial_summary_df["Mean"] = [self.mean_admission,
                                            self.mean_q_time_trial,
                                            self.mean_min,
                                            self.mean_max,
                                            self.mean_4hr,
                                            self.mean_12hr,
                                            self.mean_95,
                                            self.mean_sdec,
                                            self.mean_reneged]
        self.trial_summary_df["St. dev"] = [self.std_admission,
                                            self.std_mean_q_time_trial,
                                            self.std_min,
                                            self.std_max,
                                            self.std_4hr,
                                            self.std_12hr,
                                            self.std_95,
                                            self.std_sdec,
                                            self.std_reneged]
        self.trial_summary_df["St. error"] = [self.se_admission,
                                              self.se_mean_q_time_trial,
                                              self.se_min,
                                              self.se_max,
                                              self.se_4hr,
                                              self.se_12hr,
                                              self.se_95,
                                              self.se_sdec,
                                              self.se_reneged]
        self.trial_summary_df["Lower 95% CI"] = [self.lowerci_admission,
                                                 self.lowerci_mean_q_time_trial,
                                                 self.lowerci_min,
                                                 self.lowerci_max,
                                                 self.lowerci_4hr,
                                                 self.lowerci_12hr,
                                                 self.lowerci_95,
                                                 self.lowerci_sdec,
                                                 self.lowerci_reneged]
        self.trial_summary_df["Upper 95% CI"] = [self.upperci_admission,
                                                 self.upperci_mean_q_time_trial,
                                                 self.upperci_min,
                                                 self.upperci_max,
                                                 self.upperci_4hr,
                                                 self.upperci_12hr,
                                                 self.upperci_95,
                                                 self.upperci_sdec,
                                                 self.upperci_reneged]
        self.trial_summary_df["Min"] = [self.min_admission,
                                        self.min_mean_q_time_trial,
                                        self.min_min,
                                        self.min_max,
                                        self.min_4hr,
                                        self.min_12hr,
                                        self.min_95,
                                        self.min_sdec,
                                        self.min_reneged]
        self.trial_summary_df["Max"] = [self.max_admission,
                                        self.max_mean_q_time_trial,
                                        self.max_min,
                                        self.max_max,
                                        self.max_4hr,
                                        self.max_12hr,
                                        self.max_95,
                                        self.max_sdec,
                                        self.max_reneged]
        self.trial_summary_df = self.trial_summary_df.round(2)
        self.trial_summary_df.set_index("Metric", inplace=True)
        self.trial_summary_df.loc["4hr (DTA) Performance"] = self.trial_summary_df.loc["4hr (DTA) Performance"] * 100
        self.trial_summary_df = self.trial_summary_df.rename(index={"4hr (DTA) Performance":"4hr DTA Performance (%)"})
    

    # Method to run a trial
    def run_trial(self):
        # Run the simulation for the number of runs specified in g class.
        # For each run, we create a new instance of the Model class and call its
        # run method, which sets everything else in motion.
        results_dfs = []
        
        for run in range(g.number_of_runs):
            my_model = Model(run)
            patient_level_results = my_model.run()
            
            self.df_trial_results.loc[run] = [my_model.ed_admissions, 
                                              my_model.mean_q_time_bed,
                                              my_model.min_q_time_bed,
                                              my_model.max_q_time_bed,
                                              my_model.perf_4hr,
                                              my_model.dta_12hr,
                                              my_model.q_time_bed_95,
                                              my_model.sdec_admissions,
                                              my_model.mean_q_time_sdec,
                                              my_model.other_admissions,
                                              my_model.mean_q_time_other,
                                              my_model.reneged]

            patient_level_results = patient_level_results.round(2)
            patient_level_results['run'] = run

            results_dfs.append(patient_level_results)
        
        #stick all the individual results together
        all_results_patient_level = pd.concat(results_dfs)
                                              
        # Once the trial (ie all runs) has completed, print the final results
        #self.print_trial_results()
        #self.print_alltrial_summary()

        self.calculate_trial_summary()

        return self.df_trial_results, all_results_patient_level, self.trial_summary_df

# Create an instance of the Trial class
my_trial = Trial()

print(f"Running {g.number_of_runs} simulations......")
start_time = time.time()

# Call the run_trial method of our Trial object
df_trial_results, all_results_patient_level, trial_summary =  my_trial.run_trial()


# end_time = time.time()
# elapsed_time = end_time - start_time
# print(f"That took {round(elapsed_time)} seconds")
# print("Doing some transformations")

# #Convert wait times into hours
# all_results_patient_level['q_time_bed_hours'] = all_results_patient_level['Q Time Bed'] / 60.0
# all_results_patient_level['under4hrflag'] = np.where(all_results_patient_level['q_time_bed_hours'] < 4, 1, 0)
# all_results_patient_level['dta12hrflag'] = np.where(all_results_patient_level['q_time_bed_hours'] > 12, 1, 0)
# all_results_patient_level['q_time_bed_or_renege'] = all_results_patient_level['Q Time Bed|Renege'] / 60.0

# ################
# print("Calculating wait time metrics.....")
# print("These metrics only include those patients actually admitted")
# #calculating the metrics
# #Mean
# mean_pat_data = round(all_results_patient_level['q_time_bed_hours'].mean())

# #Min
# min_pat_data = round(all_results_patient_level['q_time_bed_hours'].min())

# #Max
# max_pat_data = round(all_results_patient_level['q_time_bed_hours'].max())

# #95th percentile
# q_pat_data = round(all_results_patient_level['q_time_bed_hours'].quantile(0.95))

# #4hr performance
# perf4hr_pat_data = "{:.0%}".format(all_results_patient_level['under4hrflag'].mean())

# #12hr DTAs per day
# dtasperday = round((all_results_patient_level['dta12hrflag'].sum() / g.number_of_runs) / 60.0)

# #Patients reneged from ED
# reneged = round(all_results_patient_level['reneged'].sum() / g.number_of_runs)

# #save these in a df
# # according to chat you want to make it into a dictionary first
# data = {
#     "Metric": ["Mean Q Time (Hrs)", "Min Q Time", "Max Q Time (Hrs)", "4hr (DTA) Performance",
#                 "12hr DTAs per day", "95th Percentile Q Time (Hrs)", "Reneged"],
#     "Results": [mean_pat_data, min_pat_data, max_pat_data, perf4hr_pat_data, 
#                 dtasperday, q_pat_data, reneged]
# }

# df = pd.DataFrame(data)

# display(df)

# #####################
# #plotting and showing a single figure

# # Create the histogram
# plt.figure(figsize=(8, 6))
# sns.histplot(all_results_patient_level['q_time_bed_hours'], bins=range(int(all_results_patient_level['q_time_bed_hours'].min()), 
#                                                       int(all_results_patient_level['q_time_bed_hours'].max()) + 1, 1), 
#              kde=False)

# # Set the boundary for the bins to start at 0
# plt.xlim(left=0)

# # Add vertical lines
# plt.axvline(x=mean_pat_data, color='tomato', linestyle='--', linewidth=1, label='Mean Q Time', zorder=0)
# plt.axvline(x=4, color='mediumturquoise', linestyle='--', linewidth=1, label='4 Hours', zorder=0)
# plt.axvline(x=12, color='royalblue', linestyle='--', linewidth=1, label='12 Hours', zorder=0)
# plt.axvline(x=q_pat_data, color='goldenrod', linestyle='--', linewidth=1, zorder=0)
# plt.axvline(x=max_pat_data, color='slategrey', linestyle='--', linewidth=1, zorder=0)

# # Add labels to the lines
# plt.text(mean_pat_data + 2, plt.ylim()[1] * 0.95, f'Mean Q Time: {mean_pat_data} hrs', color='tomato', ha='left', va='top', fontsize=10, rotation=90,
#             bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, boxstyle='round,pad=0.5'))
# plt.text(4 + 2, plt.ylim()[1] * 0.95, f'4 Hr Performance: {perf4hr_pat_data}', color='mediumturquoise', ha='left', va='top', fontsize=10, rotation=90,
#             bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, boxstyle='round,pad=0.5'))
# plt.text(12 + 2, plt.ylim()[1] * 0.95, f'12 Hr DTAs per day: {dtasperday}', color='royalblue', ha='left', va='top', fontsize=10, rotation=90,
#             bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, boxstyle='round,pad=0.5'))
# plt.text(q_pat_data + 2, plt.ylim()[1] * 0.95, f'95th Percentile Q Time: {q_pat_data} hrs', color='goldenrod', ha='left', va='top', fontsize=10, rotation=90,
#             bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, boxstyle='round,pad=0.5'))
# plt.text(max_pat_data + 1, plt.ylim()[1] * 0.95, f'Max Q Time: {max_pat_data} hrs', color='slategrey', ha='left', va='top', fontsize=10, rotation=90)

# # Add labels and title if necessary
# plt.xlabel('Admission Delays (Hours)')
# plt.ylabel('Frequency')
# plt.title('Histogram of Admission Delays')

# # Display the plot
# plt.show()

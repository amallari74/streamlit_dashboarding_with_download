One of the projects that I've done, which creates an invoice report as well as credit memo report.
Both are Billing Analytics report. Users can select the invoice month to be generated and user has an 
option to download the report via CSV file.

The code change that I've done here are listed below:
   under "download_datasets_model.py":  created "fetch_invoice_report" and "fetch_credit_memo_report" functions
   
   under "download_datasets.py":  added line 4 (to import both created functions);
                                  modified line 44 (to add the 2 reports to the dataset_options list);
                                  added the elif selected_dataset == "Invoice Report" logic;
                                  added the elif selected_dataset == "Credit Memo Report" logic

To run the application, from the shell invoke:  streamlit run src/app.py

Sample output is captured (see "generate report.png" and "download csv dataset.png")
      

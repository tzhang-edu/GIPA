Data and Code for: Achieving climate resistance in the global intertidal protected area system  
You can cite it using this DOI: 10.5281/zenodo.17131881.  
(Note: The Zenodo DOI badge will be activated upon publication)

### **Overview**  
This repository contains the core analytical scripts, processed summary datasets, and figure-generation codes supporting the manuscript "Achieving climate resistance in the global intertidal protected area system".

To facilitate peer review and ensure full reproducibility, the workflow is modularized into data extraction (Google Earth Engine), spatial modeling (Least-Cost Path Analysis), and figure generation.

Intermediate data files (e.g., global unclipped raster layers and extensive intermediate shapefiles) exceeding repository size limits are available from the corresponding author upon reasonable request.

### **Repository Structure**  
The repository is organized as follows:  
**📂 Data/**  
• Overall_Summary_260923.xlsx - Master analytical summary dataset  
• PA_info.xlsx - Basic information and metadata for Protected Areas  
• Figure1a_Bivariate_Map.csv - Plot-ready data for Figure 1a  
• Figure1b_Intermediate_data.xlsx - Plot-ready data for Figure 1b  
• Figure4a_Realm_Data.csv - Plot-ready data for Figure 4a  
• Figure4b_Transboundary_OD_Matrix_Optimized.csv - Plot-ready data for Figure 4b  
**📂 Scripts/**  
01_GEE_Processing/ - Scripts for Google Earth Engine data preprocessing  
  - GEE_data_extraction_for_global_tidal_wetland.js  
  - GEE_data_extraction_for_SLR_rate.js  
02_LCPA_Modeling/ - Scripts for Least-Cost Path Analysis and statistical modeling  
  - Scripts_for_LCPA.py  
  - Scripts_for_MonteCarlo_analysis.py  
  - Scripts_for_Basic_information_statistics.py  
03_Figure_Generation/ - Python scripts for plotting main figures  
  - plot_fig1a_en.py, plot_fig2_en.py, etc. (Individual scripts for each figure)  
**📂 Figures/**  
• Figure1b.png, Figure1cd.png, Figure2.png, Figure3.png, Figure4b.png, Figure4c.png - Output visualizations for the main text  
• Extended Data Fig_1.png through Extended Data Fig_7.png - Output visualizations for extended data 

### **Data Availability**  
During the peer-review process, raw and processed analytical data are accessible via this GitHub repository. Upon publication, all repository contents will be permanently archived with a unique DOI on Zenodo.  
#### **Third-Party Datasets**  
The third-party datasets analysed in this study are publicly available from their respective official sources:  
**Conservation \& Boundary Data:**  
• [WDPA (World Database on Protected Areas)](https://www.protectedplanet.net/)  
• [Ramsar Sites Information Service](https://rsis.ramsar.org/)  
• [Natural Earth](https://www.naturalearthdata.com/)  
• MEOW (Marine Ecoregions of the World; [Spalding et al., 2007](https://doi.org/10.1641/B570707))  
**Topography \& Oceanography Data:**  
• [Global Intertidal Datasets](https://www.intertidal.app/)  
• [DeltaDTM](https://data.4tu.nl/datasets)  
• [ETOPO2022 Global Relief Model](https://www.ncei.noaa.gov/products/etopo-global-relief-model)  
• [TPXO10-atlas-v2 (Global Tide Models)](https://www.tpxo.net/global/tpxo10-atlas)  
• Suspended Particulate Matter Data ([Wei et al., 2021](https://doi.org/10.1029/2021JC017303))  
**Climate \& Anthropogenic Data:**  
• Projected Sea-Level Rise Scenarios ([Garner et al., 2021](https://zenodo.org/records/6382554))  
• [WorldClim (Global Climate Data)](https://www.worldclim.org)  
• [Bio-ORACLE (Marine Data Layers)](https://erddap.bio-oracle.org/)  
• Global Human Modification Dataset ([Kennedy et al., 2019](https://doi.org/10.1111/gcb.14549))

### **Workflow and Usage**  
To reproduce the findings or visualizations in this study:  
•**01\_GEE\_Processing**: Execute the JavaScript/Python files in Google Earth Engine to extract and preprocess intertidal boundaries and environmental variables.  
•**02\_LCPA\_Modeling**: Run the Python scripts to perform the spatially explicit boundary adjustment simulation and calculate climate resistance.  
•**03\_Figure\_Generation**: Run the plotting scripts. The scripts are configured to read from the Data/ directory and save high-resolution outputs directly to the Figures/ directory.

### **Dependencies**  
•**Python 3.x**: numpy, pandas, geopandas, matplotlib, scikit-image (for LCPA), etc.  
•**Google Earth Engine (GEE)**: Requires a registered GEE account.  
•**ArcGIS Pro 3.6**: Used for specific spatial grid generation (e.g.'create fishnet').  

### **Contact**  
For any queries regarding the data, code, or methodology, please contact the corresponding author at tingzhang.rs@gmail.com.


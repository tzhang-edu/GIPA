Data and Code for: Achieving climate resistance in the global intertidal protected area system

You can cite it using this DOI: 10.5281/zenodo.17131881.

(Note: The Zenodo DOI badge will be activated upon publication)



### **Overview**

This repository contains the core analytical scripts, processed summary datasets, and figure-generation codes supporting the manuscript "Achieving climate resistance in the global intertidal protected area system".



To facilitate peer review and ensure full reproducibility, the workflow is modularized into data extraction (Google Earth Engine), spatial modeling (Least-Cost Path Analysis), and figure generation.



Intermediate data files (e.g., global unclipped raster layers and extensive intermediate shapefiles) exceeding repository size limits are available from the corresponding author upon reasonable request.



### **Repository Structure**

The repository is organized as follows:

```text

📂 GIPA/

├── 📊 Data/

│   ├── Master\_Baseline\_Combined\_0923\_1013\_v2.xlsx   # Final analytical dataset for 665 PAs

│   └── plot\_ready\_data\_for\_Fig4.csv                 # Plot-ready data for global mapping

├── 💻 Scripts/

│   ├── 01\_GEE\_Processing/       # Scripts for Google Earth Engine data preprocessing

│   ├── 02\_LCPA\_Modeling/        # Scripts for Least-Cost Path Analysis (Boundary adjustment)

│   └── 03\_Figure\_Generation/    # Python scripts for plotting main/extended figures

└── 📈 Figures/

&#x20;   ├── Fig\_1.pdf                # Output visualization (Main Text)

&#x20;   └── Extended\_Data\_Fig\_7.png  # Output 3D visualization (Boundary adjustment simulation)

````

### **Data Availability**

During the peer-review process, raw and processed analytical data are accessible via this GitHub repository. Upon publication, all repository contents will be permanently archived with a unique DOI on Zenodo.



#### **Third-Party Datasets**

The third-party datasets analysed in this study are publicly available from their respective official sources:



##### **Conservation \& Boundary Data:**

• [WDPA (World Database on Protected Areas)](https://www.protectedplanet.net/)

• [Ramsar Sites Information Service](https://rsis.ramsar.org/)

• [Natural Earth](https://www.naturalearthdata.com/)

• MEOW (Marine Ecoregions of the World; [Spalding et al., 2007](https://doi.org/10.1641/B570707))

##### **Topography \& Oceanography Data:**

• [Global Intertidal Datasets](https://www.intertidal.app/)

• [DeltaDTM](https://data.4tu.nl/datasets)

• [ETOPO2022 Global Relief Model](https://www.ncei.noaa.gov/products/etopo-global-relief-model)

• [TPXO10-atlas-v2 (Global Tide Models)](https://www.tpxo.net/global/tpxo10-atlas)

• Suspended Particulate Matter Data ([Wei et al., 2021](https://doi.org/10.1029/2021JC017303))

##### **Climate \& Anthropogenic Data:**

• Projected Sea-Level Rise Scenarios ([Garner et al., 2021](https://zenodo.org/records/6382554))

• [WorldClim (Global Climate Data)](https://www.worldclim.org)

• [Bio-ORACLE (Marine Data Layers)](https://erddap.bio-oracle.org/)

• Global Human Modification Dataset ([Kennedy et al., 2019](https://doi.org/10.1111/gcb.14549Digital%20Object%20Identifier%20%28DOI%29))



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


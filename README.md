# GIPA

## **About**

This repository contains the data and code to reproduce the results from Ting Zhang, ..., Zhijun Ma, et al. (2026). Achieving climate resistance in the global intertidal protected area system. In subm.



You can cite it using this DOI: [10.5281/zenodo.17131881](https://zenodo.org/records/17131881?preview=1&token=eyJhbGciOiJIUzUxMiJ9.eyJpZCI6IjViMGZjMDIxLWUxNDQtNDIzYi04NWJhLTU4MGE0MWVlOTcyOSIsImRhdGEiOnt9LCJyYW5kb20iOiJiNWExNjIwYjZlOTRmNmUzYWUwZDMwOWI4NzBmNTY2OCJ9.261kxT1B6lilLfnMCO_JTApahCUJ_-o1n7bjWCcSj_U7LfPUcG9-vyipaamYdPKIFfIMaBa1j2LP-ZjWkryT-A).

Please feel free to contact Ting Zhang (ting\_zhang@fudan.edu.cn) if you have any questions, find mistakes in the code, or if you would like to access specific files.



## **Dependencies**

To reproduce the analysis, please refer to the folder Code/, which contains the files used to produce the results. The code used for path analysis is written in Python and utilizes the arcpy site package; therefore, ArcGIS Pro must be installed on the computing platform beforehand (compatible with Windows systems only. For installation instructions, please refer to the [official guide](https://pro.arcgis.com/en/pro-app/latest/get-started/install-and-sign-in-to-arcgis-pro.htm)). Additionally, active licenses for both the Spatial Analyst (arcpy.sa) and Image Analyst (arcpy.ia) extensions are strictly required to execute the spatial operations.



Note that we have not provided raw monthly temperature data in this repository, but those data can be downloaded at [aims2.llnl.gov/search](https://metagrid.esgf-west.org/search). IPCC projected SLR data can be downloaded at [https://github.com/BrodiePearson/IPCC\_AR6\_Chapter9\_Figures](https://github.com/BrodiePearson/IPCC_AR6_Chapter9_Figures).



Note that cloning this repository may take a few minutes due to the large number of files. As the total data volume exceeds GitHub's storage limits, only a **subset** is hosted here; the complete records are available on [**Zenodo**](https://zenodo.org/records/17131881?preview=1&token=eyJhbGciOiJIUzUxMiJ9.eyJpZCI6IjViMGZjMDIxLWUxNDQtNDIzYi04NWJhLTU4MGE0MWVlOTcyOSIsImRhdGEiOnt9LCJyYW5kb20iOiJiNWExNjIwYjZlOTRmNmUzYWUwZDMwOWI4NzBmNTY2OCJ9.261kxT1B6lilLfnMCO_JTApahCUJ_-o1n7bjWCcSj_U7LfPUcG9-vyipaamYdPKIFfIMaBa1j2LP-ZjWkryT-A).



We have tested in ArcGIS Pro 10.3 and MATLAB R2023b on Windows 11 (on PC with i7-13700 and 32 GB memory). Below is an overview of the different folders in this repository and their content.



## **File 1: Data/**

This folder contains data used to perform the analyses and run the code.

### ----- Protected areas data -----

• **WDPA\_May2023\_Public\_shp\_polygons\_international\_level.shp** (subset): spatial extent of PAs. The attribute table of these data is detailed below:

|No.|Attributes|Data type|Description|
|-|-|-|-|
|1|Shape|Geometry|Vector type, here is 'polygon'|
|2|WDPAID|Double|Unique ID number of the PA|
|3|WDPA\_PID|Text|Unique ID number of the PA (different data types)|
|4|NAME|Text|Name of PA (in English)|
|5|ORIG\_NAME|Text|Name of PA (in non-English)|
|6|DESIG|Text|Designation of PA|
|7|DESIG\_ENG|Text|Designation of PA (in English)|
|8|DESIG\_TYPE|Text|Type of PA, here is 'International'|
|9|ISO3|Text|Country in which PA is located|



**• WDPA\_May2023\_Public\_shp\_polygons\_international\_level\_grid.shp** (subset): the vector surface data of the computational grid. Owing to the large amount of data, the file is saved in the geodatabase and then called for calculation during actual operation. The attribute table of these data is as follows:

|No.|Attributes|Data type|Description|
|-|-|-|-|
|1|Shape|Geometry|Vector type, here is 'polygon'|
|2|WDPAID|Double|Unique ID number of the PA|
|3|WDPA\_PID|Text|Unique ID number of the PA (different data types)|
|4|NAME|Text|Name of PA (in English)|
|5|ISO3|Text|Country in which PA is located|
|6|WDPA\_PID2|Text|Unique ID for each computing grid, including WDPAID information|

#### 

### ----- Inundation frequency data------

**• ETOPO\_2022\_v1\_30s\_N90W180\_bed.tif** (subset): Global topographic data.

**• Fig9\_28b\_data\_resample.tif** (subset): Sea level rise values for the year 2100 under the SSP1-2.6 scenario.

**• Fig9\_28c\_data\_resample.tif** (subset): Sea level rise values for the year 2100 under the SSP2-4.5 scenario.

**• Fig9\_28d\_data\_resample.tif** (subset): Sea level rise values for the year 2100 under the SSP3-7.0 scenario.

**• Fig9\_28e\_data\_resample.tif** (subset): Sea level rise values for the year 2100 under the SSP5-8.5 scenario.

• **Inundation\_frequency\_global\_2010.tif** (subset): Inundation frequency for the year 2010.

**• Inundation\_frequency\_global\_ssp126\_2100.tif** (subset): Inundation frequency for the year 2100 under the SSP1-2.6 scenario.

**• Inundation\_frequency\_global\_ssp245\_2100.tif** (subset): Inundation frequency for the year 2100 under the SSP2-4.5 scenario.

**• Inundation\_frequency\_global\_ssp370\_2100.tif** (subset): Inundation frequency for the year 2100 under the SSP3-7.0 scenario.

**• Inundation\_frequency\_global\_ssp585\_2100.tif** (subset): Inundation frequency for the year 2100 under the SSP5-8.5 scenario.



### -----Air temperature data------

**• resample\_converted\_tas\_Amon\_CNRM-CM6-1-HR\_historical\_r1i1p1f2\_gr\_2010.tif** (subset): Global temperature data layer for the year 2010.

**• resample\_converted\_tas\_Amon\_CNRM-CM6-1-HR\_ssp126\_r1i1p1f2\_gr\_2100.tif** (subset): Global temperature data for the year 2100 under the SSP1-2.6 scenario.

**• resample\_converted\_tas\_Amon\_CNRM-CM6-1-HR\_ssp245\_r1i1p1f2\_gr\_2100.tif** (subset): Global temperature data for the year 2100 under the SSP2-4.5 scenario.

**• resample\_converted\_tas\_Amon\_CNRM-CM6-1-HR\_ssp370\_r1i1p1f2\_gr\_2100.tif** (subset): Global temperature data for the year 2100 under the SSP3-7.0 scenario.

**• resample\_converted\_tas\_Amon\_CNRM-CM6-1-HR\_ssp585\_r1i1p1f2\_gr\_2100.tif** (subset): Global temperature data for the year 2100 under the SSP5-8.5 scenario.



### ------ Human pressure data -----

**• gHM.tif** (subset): the global human modification (HM) dataset created by Kennedy et al. (2019).





## **File 2: Code/**

### Code/MATLAB

This folder contains all the MATLAB code needed for data preprocessing.

**• Preprocessing\_for\_SLR\_data.m**: Preprocessing the latitude and longitude display formats of the raw sea level rise data.



### Code/Python

This folder contains all the Python code needed to reproduce the results.

**• cost\_path\_analysis\_for\_SLR\_Warming.py**: Used for batch analysis of the path analysis considering both the impacts of sea level rise and warming.

**• validate\_and\_cost\_path\_as\_polyline.py**: A submodel that needs to be called during path analysis, which is primarily used to ensure that when a computational grid has no path, the error is skipped and the next cell is processed in the batch calculation.





## **File 3: Results**

This folder contains all the (subset) code outputs considering both sea level rise and warming.

### -----Climate resistance------

**• Climate\_resistance:**

**•ssp126\_s\_w.shp** (subset): Extent of intertidal PAs achieving climate resistance internally without any management action under SSP1-2.6. The corresponding data were directly excluded from subsequent analyses under the corresponding scenarios.



The attribute tables for the above data are all the same, as follows:

|No.|Attributes|Data type|Description|
|-|-|-|-|
|1|Shape|Geometry|Vector type, here is 'Point'|
|2|WDPAID|Double|Unique ID number of the PA|
|3|WDPA\_PID|Text|Unique ID number of the PA (different data types)|
|4|GroupID|Text|Unique ID for each computational grid, including WDPAID information. This ID is the same as 'WDPA\_PID2' in the shapefile of the computational grid|
|5|WDPA\_PID2|Text|Unique ID for each computing grid, including WDPAID information|
|6|T2010|Double|Temperature in the baseline year (2010)|
|7|T\_SSP126|Double|Temperature in 2100 under the SSP1-2.6 scenario|
|8|T\_SSP245|Double|Temperature in 2100 under the SSP2-4.5 scenario|
|9|T\_SSP370|Double|Temperature in 2100 under the SSP3-7.0 scenario|
|10|T\_SSP585|Double|Temperature in 2100 under the SSP5-8.5 scenario|
|11|I2010|Double|Immersion frequency in the baseline year (2010)|
|12|I\_SSP126|Double|Immersion frequency in 2100 under the SSP1-2.6 scenario|
|13|I\_SSP245|Double|Immersion frequency in 2100 under the SSP2-4.5 scenario|
|14|I\_SSP370|Double|Immersion frequency in 2100 under the SSP3-7.0 scenario|
|15|I\_SSP585|Double|Immersion frequency in 2100 under the SSP5-8.5 scenario|



**• Climate\_resistance\_BA:**

**• ssp126\_s\_w\_BA.shp** (subset): Paths of intertidal PAs achieving climate resistance via boundary adjustments under the SSP1-2.6 scenario.

**• ssp245\_s\_w\_BA.shp** (subset): Paths of intertidal PAs achieving climate resistance via boundary adjustments under the SSP2-4.5 scenario.

**• ssp370\_s\_w\_BA.shp** (subset): Paths of intertidal PAs achieving climate resistance via boundary adjustments under the SSP3-7.0 scenario.

**• ssp585\_s\_w\_BA.shp** (subset): Paths of intertidal PAs achieving climate resistance via boundary adjustments under the SSP5-8.5 scenario.



The attribute tables for the above data are all the same, as follows:

|No.|Attributes|Data type|Description|
|-|-|-|-|
|1|Shape|Geometry|Vector type, here is 'Polyline'|
|2|GroupID|Text|Unique ID for each computational grid, including WDPAID information. This ID is the same as 'WDPA\_PID2' in the shapefile of the computational grid|
|3|WDPAID|Text|Unique ID number of the PA|
|4|PathCost|Double|Path cost|

###### 

**• Climate\_resistance\_BA\_MR1**:

• **ssp126\_s\_w\_ BA\_MR1.shp** (subset): Paths of intertidal PAs achieving climate resistance via boundary adjustments and moderate-intensity managed realignment under the SSP1-2.6 scenario.

• **ssp245\_s\_w\_ BA\_MR1.shp** (subset): Paths of intertidal PAs achieving climate resistance via boundary adjustments and moderate-intensity managed realignment under the SSP2-4.5 scenario.

**• ssp370\_s\_w\_ BA\_MR1.shp** (subset): Paths of intertidal PAs achieving climate resistance via boundary adjustments and moderate-intensity managed realignment under the SSP3-7.0 scenario.

**• ssp585\_s\_w\_ BA\_MR1.shp** (subset): Paths of intertidal PAs achieving climate resistance via boundary adjustments and moderate-intensity managed realignment under the SSP5-8.5 scenario.



The attribute tables for the above data are all the same, as follows:

|No.|Attributes|Data type|Description|
|-|-|-|-|
|1|Shape|Geometry|Vector type, here is 'Polyline'|
|2|GroupID|Text|Unique ID for each computational grid, including WDPAID information. This ID is the same as 'WDPA\_PID2' in the shapefile of the computational grid|
|3|WDPAID|Text|Unique ID number of the PA|

###### 

**• Climate\_resistance\_ BA\_MR2:**

**• ssp126\_s\_w\_ BA\_MR2.shp** (subset): Paths of intertidal PAs achieving climate resistance via boundary adjustments and high-intensity managed realignment under the SSP1-2.6 scenario.

**• ssp245\_s\_w\_ BA\_MR2.shp** (subset): Paths of intertidal PAs achieving climate resistance via boundary adjustments and high-intensity managed realignment under the SSP2-4.5 scenario.

**• ssp370\_s\_w\_ BA\_MR2.shp** (subset): Paths of intertidal PAs achieving climate resistance via boundary adjustments and high-intensity managed realignment under the SSP3-7.0 scenario.

**• ssp585\_s\_w\_ BA\_MR2.shp** (subset): Paths of intertidal PAs achieving climate resistance via boundary adjustments and high-intensity managed realignment under the SSP5-8.5 scenario.



The attribute tables for the above data are all the same, as follows:

|No.|Attributes|Data type|Description|
|-|-|-|-|
|1|Shape|Geometry| Vector type, here is 'Polyline'|
|2|GroupID|Text|Unique ID for each computational grid, including WDPAID information. This ID is the same as 'WDPA\_PID2' in the shapefile of the computational grid|
|3|WDPAID|Text|Unique ID number of the PA|
|4|PathCost|Double|Path cost|

#### 

### ----- Summarized data -----

**• Statistics on air temperature and sea level rise.xlsx**: The area of each intertidal PA, along with its latitude and longitude, the air temperature in 2010, the predicted temperature for the year 2100 under the four scenarios, the predicted sea level rise values for 2100 under the four scenarios, and the area lost due to sea level rise;

**• Statistics of climate resistance.xlsx**: the area and number of intertidal PAs that achieve climate resistance internally and those requiring specific management interventions.

**• Statistics of climate resistance by ecoregion.xlsx**: Climate resistance percentage of intertidal PAs per ecoregion, considering the combined impacts of SLR and warming across four GHG emission scenarios.





## **File 4: Figure/**

This folder contains figure outputs for the main figures and extended data figures.


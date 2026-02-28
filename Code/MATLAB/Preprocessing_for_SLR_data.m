%% Release date: March 30, 2025
%% Author: Ting Zhang
clc
clear

%% Show structure
ncFilePath='…\Fig9-28c_data.nc'; % storage location
ncdisp(ncFilePath); 
S=ncinfo(ncFilePath);
S.Format='netcdf4';

%% Read variable value
lon=ncread(ncFilePath,'Longitude'); % Read the longitude variable
lat=ncread(ncFilePath,'Latitude'); % Reading the latitude variable
slr=ncread(ncFilePath,'SL_Change'); % Read SLR variables
lon=lon(1:360,1);
slr=slr(1:180,1:360);
ncdisp(ncFilePath) 

%% Renaming dimensions, variables, and attributes % 
ncid2=netcdf.create('Fig9-28a_data_new.nc','NC_NOCLOBBER');
dimidy=netcdf.defDim(ncid2,'Latitude',180);
dimidx=netcdf.defDim(ncid2,'Longitude',360);
varid_SL=netcdf.defVar(ncid2,'SL_Change','double',[dimidy,dimidx]);
varid_Lat=netcdf.defVar(ncid2,'Latitude','double',dimidy);
varid_Lon=netcdf.defVar(ncid2,'Longitude','double',dimidx);
netcdf.endDef(ncid2);
netcdf.putVar(ncid2,varid_Lon,lon);  
netcdf.putVar(ncid2,varid_Lat,lat);  
netcdf.putVar(ncid2,varid_SL,slr); 
S=ncinfo(ncFilePath);
S.Format='netcdf4';
netcdf.close(ncid2);
ncFilePath2='…\Fig9-28a_data_new.nc'; % storage location
ncdisp(ncFilePath2);
%% END

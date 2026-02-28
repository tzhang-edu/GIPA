# -*- coding: utf-8 -*-
import arcpy
from arcpy.ia import *
from arcpy.sa import *
from sys import argv
import sys
import os

# Update sys.path to ensure that it includes the path to your script.
sys.path.append(r"...Enter the path to the folder where the code is located...")

# Import the script name of the sub-model
import validate_and_cost_path_as_polyline 

# Define the model.
def FinalModel(Buffer500="memory\\Buffer500", d2100="memory\\d2100"): 

    # To allow overwriting outputs change overwriteOutput option to True.
    arcpy.env.overwriteOutput = True

    # Check out any necessary licenses.
    arcpy.CheckOutExtension("spatial")
    arcpy.CheckOutExtension("ImageAnalyst")

    # Model Environment settings
    with arcpy.EnvManager(parallelProcessingFactor="100%"):
    
        Tx = "....gdb\\WDPA_May2023_Public_shp_polygons_international_level_grid"

        tas_2010 = arcpy.Raster("...\\resample_converted_tas_Amon_CNRM-CM6-1-HR_historical_r1i1p1f2_gr_2010.tif")
        tas_2020 = arcpy.Raster("...\\resample_converted_tas_Amon_CNRM-CM6-1-HR_ssp126_r1i1p1f2_gr_2020.tif")
        tas_2030 = arcpy.Raster("...\\resample_converted_tas_Amon_CNRM-CM6-1-HR_ssp126_r1i1p1f2_gr_2030.tif")
        tas_2040 = arcpy.Raster("...\\resample_converted_tas_Amon_CNRM-CM6-1-HR_ssp126_r1i1p1f2_gr_2040.tif")
        tas_2050 = arcpy.Raster("...\\resample_converted_tas_Amon_CNRM-CM6-1-HR_ssp126_r1i1p1f2_gr_2050.tif")
        tas_2060 = arcpy.Raster("...\\resample_converted_tas_Amon_CNRM-CM6-1-HR_ssp126_r1i1p1f2_gr_2060.tif")        
        tas_2070 = arcpy.Raster("...\\resample_converted_tas_Amon_CNRM-CM6-1-HR_ssp126_r1i1p1f2_gr_2070.tif")
        tas_2080 = arcpy.Raster("...\\resample_converted_tas_Amon_CNRM-CM6-1-HR_ssp126_r1i1p1f2_gr_2080.tif")
        tas_2090 = arcpy.Raster("...\\resample_converted_tas_Amon_CNRM-CM6-1-HR_ssp126_r1i1p1f2_gr_2090.tif")
        tas_2100 = arcpy.Raster("...\\resample_converted_tas_Amon_CNRM-CM6-1-HR_ssp126_r1i1p1f2_gr_2100.tif")
        
        ind_2010 = arcpy.Raster("...\\Inundation_frequency_global_ssp126_2010.tif")
        ind_2020 = arcpy.Raster("...\\Inundation_frequency_global_ssp126_2020.tif")
        ind_2030 = arcpy.Raster("...\\Inundation_frequency_global_ssp126_2030.tif")
        ind_2040 = arcpy.Raster("...\\Inundation_frequency_global_ssp126_2040.tif")
        ind_2050 = arcpy.Raster("...\\Inundation_frequency_global_ssp126_2050.tif")
        ind_2060 = arcpy.Raster("...\\Inundation_frequency_global_ssp126_2060.tif")
        ind_2070 = arcpy.Raster("...\\Inundation_frequency_global_ssp126_2070.tif")
        ind_2080 = arcpy.Raster("...\\Inundation_frequency_global_ssp126_2080.tif")
        ind_2090 = arcpy.Raster("...\\Inundation_frequency_global_ssp126_2090.tif")
        ind_2100 = arcpy.Raster("...\\Inundation_frequency_global_ssp126_2100.tif")


        # Start querying to loop through all the WDPA_PID2.
        with arcpy.da.SearchCursor(Tx, ["SHAPE@", "WDPA_PID2"]) as cursor:
            for I_fishnetIntersect, Value in cursor:
                # Debug, confirm the current processing item
                print(f"Processing WDPA_PID2: {Value}")  

                # Output file name
                _Value_shp = fr"....gdb\WDPA_May2023_Public_shp_polygons_international_level_grid\{Value}.shp"

                # Process: Buffer (Buffer) (analysis)
                Buffer1km = "memory\\Buffer1km"
                arcpy.analysis.Buffer(in_features=I_fishnetIntersect, out_feature_class=Buffer1km, buffer_distance_or_field="1 Kilometers")

                # Process: Clip Raster (Clip Raster) (management)
                temp2010_1km = "memory\\temp2010_1km"
                arcpy.management.Clip(in_raster=tas_2010, 
                                       rectangle="-65.3493337753999 -43.9750220004998 -64.6410004448998 -43.3083553364997", 
                                       out_raster=temp2010_1km, 
                                       in_template_dataset=Buffer1km, 
                                       clipping_geometry="ClippingGeometry", 
                                       maintain_clipping_extent="MAINTAIN_EXTENT")
                temp2010_1km = arcpy.Raster(temp2010_1km)


                # Process: Clip Raster (Clip Raster) (management)
                innu_2010_1km = "memory\\innu_2010_1km"
                arcpy.management.Clip(in_raster=Ind_2010,
                                      rectangle="-78.2590586292646 22.5742807561988 -78.2393850945068 22.6001002915372",
                                      out_raster=innu_2010_1km,
                                      in_template_dataset=Buffer1km,
                                      clipping_geometry="NONE",
                                      maintain_clipping_extent="MAINTAIN_EXTENT")
                innu_2010_1km = arcpy.Raster(innu_2010_1km)

                # Process: Buffer (Buffer) (analysis)
                # Get extent
                extent = I_fishnetIntersect.extent
                with arcpy.EnvManager(extent=extent):
                    arcpy.analysis.Buffer(in_features=I_fishnetIntersect,
                    out_feature_class=Buffer500.__str__().format(**locals(),**globals())if
                    isinstance(Buffer500, str) else Buffer500,
                    buffer_distance_or_field="500 Kilometers")

                # Process: Get Raster Properties  (Get Raster Properties) (management)
                Property_2_ = arcpy.management.GetRasterProperties(in_raster=temp2010_1km, property_type="MEAN")[0]

                # Process: Get Raster Properties (Get Raster Properties) (management)
                Property = arcpy.management.GetRasterProperties(in_raster=Innu_2010_1km, property_type="MEAN")[0]
     
                # Process: Clip Raster (Clip Raster) (management)
                temp2010 = "memory\\temp2010"
                arcpy.management.Clip(in_raster=tas_2010, rectangle="-65.3493337753999 -43.9750220004998 -64.6410004448998 -43.3083553364997",
                                      out_raster=temp2010, in_template_dataset=Buffer500.__str__().format(**locals(),**globals())if isinstance(Buffer500, str) else Buffer500,
                                      clipping_geometry="ClippingGeometry", maintain_clipping_extent="MAINTAIN_EXTENT")
                temp2010 = arcpy.Raster(temp2010)

                # Process: Clip Raster (Clip Raster) (management)
                innu_2010 = "memory\\innu_2010"
                arcpy.management.Clip(in_raster=ind_2010, rectangle="-83.1120682689007 18.0669587702133 -73.386502762243 27.1048866751727",
                                      out_raster=innu_2010, in_template_dataset=Buffer500.__str__().format(**locals(),**globals())if isinstance(Buffer500, str) else Buffer500,
                                      clipping_geometry="ClippingGeometry", maintain_clipping_extent="MAINTAIN_EXTENT")
                innu_2010 = arcpy.Raster(innu_2010)


                # Process: Raster Calculator (Raster Calculator)(ia)
                cost2010st = "memory\\cost2010st"
                Raster_Calculator = cost2010st
                cost2010st = ((Abs(Abs(temp2010- float(Property_2_))* 2) + 1))*((Abs(Abs(Innu_2010- int(float(Property)))* 0.05) + 1))
                cost2010st.save(Raster_Calculator)

                # Process: Clip Raster (Clip Raster) (management)
                temp2020 = "memory\\temp2020"
                arcpy.management.Clip(in_raster=tas_2020, rectangle="-65.3493337753999 -43.9750220004998 -64.6410004448998 -43.3083553364997",
                                      out_raster=temp2020, in_template_dataset=Buffer500.__str__().format(**locals(),**globals())if isinstance(Buffer500, str) else Buffer500,
                                      clipping_geometry="ClippingGeometry", maintain_clipping_extent="MAINTAIN_EXTENT")
                temp2020 = arcpy.Raster(temp2020)

                # Process: Clip Raster (Clip Raster) (management)
                innu_2020 = "memory\\innu_2020"
                arcpy.management.Clip(in_raster=ind_2020, rectangle="-83.1120682689007 18.0669587702133 -73.386502762243 27.1048866751727",
                                      out_raster=Innu_2020, in_template_dataset=Buffer500.__str__().format(**locals(),**globals())if isinstance(Buffer500, str) else Buffer500,
                                      clipping_geometry="ClippingGeometry", maintain_clipping_extent="MAINTAIN_EXTENT")
                innu_2020 = arcpy.Raster(innu_2020)

                # Process: Raster Calculator (Raster Calculator)(ia)
                cost2020st = "memory\\cost2020st"
                Raster_Calculator_2_ = cost2020st
                cost2020st = ((Abs(Abs(temp2020- float(Property_2_))* 2) + 1))*((Abs(Abs(Innu_2020- int(float(Property)))* 0.05) + 1))
                cost2020st.save(Raster_Calculator_2_)

                # Process: Clip Raster  (Clip Raster) (management)
                temp2030 = "memory\\temp2030"
                arcpy.management.Clip(in_raster=tas_2030, rectangle="-65.3493337753999 -43.9750220004998 -64.6410004448998 -43.3083553364997",
                                      out_raster=temp2030, in_template_dataset=Buffer500.__str__().format(**locals(),**globals())if isinstance(Buffer500, str) else Buffer500,
                                      clipping_geometry="ClippingGeometry", maintain_clipping_extent="MAINTAIN_EXTENT")
                temp2030 = arcpy.Raster(temp2030)

                # Process: Clip Raster (Clip Raster) (management)
                innu_2030 = "memory\\innu_2030"
                arcpy.management.Clip(in_raster=ind_2030, rectangle="-83.1120682689007 18.0669587702133 -73.386502762243 27.1048866751727",
                                      out_raster=innu_2030, in_template_dataset=Buffer500.__str__().format(**locals(),**globals())if isinstance(Buffer500, str) else Buffer500,
                                      clipping_geometry="ClippingGeometry", maintain_clipping_extent="MAINTAIN_EXTENT")
                innu_2030 = arcpy.Raster(innu_2030)

                # Process: Raster Calculator (Raster Calculator) (ia)
                cost2030st = "memory\\cost2030st"
                Raster_Calculator_3_ = cost2030st
                cost2030st = ((Abs(Abs(temp2030- float(Property_2_))* 2) + 1))*((Abs(Abs(Innu_2030- int(float(Property)))* 0.05) + 1))
                cost2030st.save(Raster_Calculator_3_)

                # Process: Clip Raster  (Clip Raster) (management)
                temp2040 = "memory\\temp2040"
                arcpy.management.Clip(in_raster=tas_2040, rectangle="-65.3493337753999 -43.9750220004998 -64.6410004448998 -43.3083553364997",
                                      out_raster=temp2040, in_template_dataset=Buffer500.__str__().format(**locals(),**globals())if isinstance(Buffer500, str) else Buffer500,
                                      clipping_geometry="ClippingGeometry", maintain_clipping_extent="MAINTAIN_EXTENT")
                temp2040 = arcpy.Raster(temp2040)

                # Process: Clip Raster  (Clip Raster) (management)
                innu_2040 = "memory\\innu_2040"
                arcpy.management.Clip(in_raster=ind_2040, rectangle="-83.1120682689007 18.0669587702133 -73.386502762243 27.1048866751727",
                                      out_raster=innu_2040, in_template_dataset=Buffer500.__str__().format(**locals(),**globals())if isinstance(Buffer500, str) else Buffer500,
                                      clipping_geometry="ClippingGeometry", maintain_clipping_extent="MAINTAIN_EXTENT")
                innu_2040 = arcpy.Raster(innu_2040)

                # Process: Raster Calculator  (Raster Calculator) (ia)
                cost2040st = "memory\\cost2040st"
                Raster_Calculator_4_ = cost2040st
                cost2040st = ((Abs(Abs(temp2040- float(Property_2_))* 2) + 1))*((Abs(Abs(Innu_2040- int(float(Property)))* 0.05) + 1))
                cost2040st.save(Raster_Calculator_4_)

                # Process: Clip Raster (Clip Raster) (management)
                temp2050 = "memory\\temp2050"
                arcpy.management.Clip(in_raster=tas_2050, rectangle="-65.3493337753999 -43.9750220004998 -64.6410004448998 -43.3083553364997",
                                      out_raster=temp2050, in_template_dataset=Buffer500.__str__().format(**locals(),**globals())if isinstance(Buffer500, str) else Buffer500,
                                      clipping_geometry="ClippingGeometry", maintain_clipping_extent="MAINTAIN_EXTENT")
                temp2050 = arcpy.Raster(temp2050)

                # Process: Clip Raster (Clip Raster) (management)
                innu_2050 = "memory\\innu_2050"
                arcpy.management.Clip(in_raster=ind_2050, rectangle="-83.1120682689007 18.0669587702133 -73.386502762243 27.1048866751727",
                                      out_raster=innu_2050, in_template_dataset=Buffer500.__str__().format(**locals(),**globals())if isinstance(Buffer500, str) else Buffer500,
                                      clipping_geometry="ClippingGeometry", maintain_clipping_extent="MAINTAIN_EXTENT")
                innu_2050 = arcpy.Raster(innu_2050)

                # Process: Raster Calculator (Raster Calculator) (ia)
                cost2050st = "memory\\cost2050st"
                Raster_Calculator_5_ = cost2050st
                cost2050st = ((Abs(Abs(temp2050- float(Property_2_))* 2) + 1))*((Abs(Abs(Innu_2050- int(float(Property)))* 0.05) + 1))
                cost2050st.save(Raster_Calculator_5_)

                # Process: Clip Raster  (Clip Raster) (management)
                temp2060 = "memory\\temp2060"
                arcpy.management.Clip(in_raster=tas_2060, rectangle="-65.3493337753999 -43.9750220004998 -64.6410004448998 -43.3083553364997",
                                      out_raster=temp2060, in_template_dataset=Buffer500.__str__().format(**locals(),**globals())if isinstance(Buffer500, str) else Buffer500,
                                      clipping_geometry="ClippingGeometry", maintain_clipping_extent="MAINTAIN_EXTENT")
                temp2060 = arcpy.Raster(temp2060)

                # Process: Clip Raster (Clip Raster) (management)
                innu_2060 = "memory\\innu_2060"
                arcpy.management.Clip(in_raster=Ind_2060, rectangle="-83.1120682689007 18.0669587702133 -73.386502762243 27.1048866751727",
                                      out_raster=Innu_2060, in_template_dataset=Buffer500.__str__().format(**locals(),**globals())if isinstance(Buffer500, str) else Buffer500,
                                      clipping_geometry="ClippingGeometry", maintain_clipping_extent="MAINTAIN_EXTENT")
                innu_2060 = arcpy.Raster(innu_2060)

                # Process: Raster Calculator (6) (Raster Calculator) (ia)
                cost2060st = "memory\\cost2060st"
                Raster_Calculator_6_ = cost2060st
                cost2060st = ((Abs(Abs(temp2060- float(Property_2_))* 2) + 1))*((Abs(Abs(Innu_2060- int(float(Property)))* 0.05) + 1))
                cost2060st.save(Raster_Calculator_6_)
   
                # Process: Clip Raster (Clip Raster) (management)
                temp2070 = "memory\\temp2070"
                arcpy.management.Clip(in_raster=tas_2070, rectangle="-65.3493337753999 -43.9750220004998 -64.6410004448998 -43.3083553364997",
                                      out_raster=temp2070, in_template_dataset=Buffer500.__str__().format(**locals(),**globals())if isinstance(Buffer500, str) else Buffer500,
                                      clipping_geometry="ClippingGeometry", maintain_clipping_extent="MAINTAIN_EXTENT")
                temp2070 = arcpy.Raster(temp2070)

                # Process: Clip Raster (Clip Raster) (management)
                innu_2070 = "memory\\innu_2070"
                arcpy.management.Clip(in_raster=ind_2070, rectangle="-83.1120682689007 18.0669587702133 -73.386502762243 27.1048866751727",
                                      out_raster=innu_2070, in_template_dataset=Buffer500.__str__().format(**locals(),**globals())if isinstance(Buffer500, str) else Buffer500,
                                      clipping_geometry="ClippingGeometry", maintain_clipping_extent="MAINTAIN_EXTENT")
                innu_2070 = arcpy.Raster(innu_2070)

                # Process: Raster Calculator (Raster Calculator) (ia)
                cost2070st = "memory\\cost2070st"
                Raster_Calculator_7_ = cost2070st
                cost2070st = ((Abs(Abs(temp2070- float(Property_2_))* 2) + 1))*((Abs(Abs(Innu_2070- int(float(Property)))* 0.05) + 1))
                cost2070st.save(Raster_Calculator_7_)

                # Process: Clip Raster  (Clip Raster) (management)
                temp2080 = "memory\\temp2080"
                arcpy.management.Clip(in_raster=tas_2080, rectangle="-65.3493337753999 -43.9750220004998 -64.6410004448998 -43.3083553364997",
                                      out_raster=temp2080, in_template_dataset=Buffer500.__str__().format(**locals(),**globals())if isinstance(Buffer500, str) else Buffer500,
                                      clipping_geometry="ClippingGeometry", maintain_clipping_extent="MAINTAIN_EXTENT")
                temp2080 = arcpy.Raster(temp2080)

                # Process: Clip Raster (Clip Raster) (management)
                innu_2080 = "memory\\innu_2080"
                arcpy.management.Clip(in_raster=ind_2080, rectangle="-83.1120682689007 18.0669587702133 -73.386502762243 27.1048866751727",
                                      out_raster=innu_2080, in_template_dataset=Buffer500.__str__().format(**locals(),**globals())if isinstance(Buffer500, str) else Buffer500,
                                      clipping_geometry="ClippingGeometry", maintain_clipping_extent="MAINTAIN_EXTENT")
                innu_2080 = arcpy.Raster(innu_2080)

                # Process: Raster Calculator  (Raster Calculator) (ia)
                cost2080st = "memory\\cost2080st"
                Raster_Calculator_8_ = cost2080st
                cost2080st = ((Abs(Abs(temp2080- float(Property_2_))* 2) + 1))*((Abs(Abs(Innu_2080- int(float(Property)))* 0.05) + 1))
                cost2080st.save(Raster_Calculator_8_)

                # Process: Clip Raster (Clip Raster) (management)
                temp2090 = "memory\\temp2090"
                arcpy.management.Clip(in_raster=tas_2090, rectangle="-65.3493337753999 -43.9750220004998 -64.6410004448998 -43.3083553364997",
                                      out_raster=temp2090, in_template_dataset=Buffer500.__str__().format(**locals(),**globals())if isinstance(Buffer500, str) else Buffer500,
                                      clipping_geometry="ClippingGeometry", maintain_clipping_extent="MAINTAIN_EXTENT")
                temp2090 = arcpy.Raster(temp2090)

                # Process: Clip Raster  (Clip Raster) (management)
                innu_2090 = "memory\\innu_2090"
                arcpy.management.Clip(in_raster=ind_2090, rectangle="-83.1120682689007 18.0669587702133 -73.386502762243 27.1048866751727",
                                      out_raster=innu_2090, in_template_dataset=Buffer500.__str__().format(**locals(),**globals())if isinstance(Buffer500, str) else Buffer500,
                                      clipping_geometry="ClippingGeometry", maintain_clipping_extent="MAINTAIN_EXTENT")
                innu_2090 = arcpy.Raster(innu_2090)

                # Process: Raster Calculator (Raster Calculator) (ia)
                cost2090st = "memory\\cost2090st"
                Raster_Calculator_9_ = cost2090st
                cost2090st = ((Abs(Abs(temp2090- float(Property_2_))* 2) + 1))*((Abs(Abs(Innu_2090- int(float(Property)))* 0.05) + 1))
                cost2090st.save(Raster_Calculator_9_)
                
                # Process: Clip Raster (Clip Raster) (management)
                temp2100 = "memory\\temp2100"
                arcpy.management.Clip(in_raster=tas_2100, rectangle="-65.3493337753999 -43.9750220004998 -64.6410004448998 -43.3083553364997",
                                      out_raster=temp2100, in_template_dataset=Buffer500.__str__().format(**locals(),**globals())if isinstance(Buffer500, str) else Buffer500,
                                      clipping_geometry="ClippingGeometry", maintain_clipping_extent="MAINTAIN_EXTENT")
                temp2100 = arcpy.Raster(temp2100)

                # Process: Clip Raster (Clip Raster) (management)
                innu_2100 = "memory\\innu_2100"
                arcpy.management.Clip(in_raster=ind_2100, rectangle="-83.1120682689007 18.0669587702133 -73.386502762243 27.1048866751727",
                                      out_raster=innu_2100, in_template_dataset=Buffer500.__str__().format(**locals(),**globals())if isinstance(Buffer500, str) else Buffer500,
                                      clipping_geometry="ClippingGeometry", maintain_clipping_extent="MAINTAIN_EXTENT")
                innu_2100 = arcpy.Raster(innu_2100)

                # Process: Raster Calculator (Raster Calculator) (ia)
                cost2100st = "memory\\cost2100st"
                Raster_Calculator_10_ = cost2100st
                cost2100st = ((Abs(Abs(temp2100- float(Property_2_))* 2) + 1))*((Abs(Abs(Innu_2100- int(float(Property)))* 0.05) + 1))
                cost2100st.save(Raster_Calculator_10_)

                cost_st_2_ = "memory\\cost_st"
                Cell_Statistics = cost_st_2_
                cost_st_2_ = arcpy.ia.CellStatistics([cost2010st, cost2020st, cost2030st, cost2040st, cost2050st, cost2060st, cost2070st, cost2080st, cost2090st, cost2100st],
                                                     "MINIMUM", "DATA", "SINGLE_BAND", 90, "AUTO_DETECT")
                cost_st_2_.save(Cell_Statistics)


                cd_st = "memory\\cd_st"
                Distance_Accumulation = cd_st
                bl_st = "memory\\bl_st"
                sd_Value_tif = ""
                sl_Value_tif = ""
                cd_st = arcpy.sa.DistanceAccumulation(temp2010_1km, "", "", cost_st_2_, "", "BINARY 1 -30 30", "", "BINARY 1 45", bl_st, sd_Value_tif, sl_Value_tif, "", "", "", "", "PLANAR")
                cd_st.save(Distance_Accumulation)
                bl_st = arcpy.Raster(bl_st)
                
                # Process: Raster Calculator (Raster Calculator) (ia)
                c2100_t = "memory\\c2100_t"
                Raster_Calculator_11_ = c2100_t
                c2100_t = Con((temp2100>=(float(Property_2_)-0.25)) & (temp2100<=(float(Property_2_)+0.25)),temp2100,None)
                c2100_t.save(Raster_Calculator_11_)

                # Process: Raster Calculator (Raster Calculator) (ia)
                c2100_s = "memory\\c2100_s"
                Raster_Calculator_32_ = c2100_s
                c2100_s = Con((Innu_2100>=(float(Property)-10)) & (Innu_2100<=(float(Property)+10)),Innu_2100,None)
                c2100_s.save(Raster_Calculator_32_)
               
                # Process: Raster to Point (Raster to Point) (conversion)
                d2100_t = "memory\\d2100_t"
                with arcpy.EnvManager(outputMFlag="Disabled", outputZFlag="Disabled"):
                    arcpy.conversion.RasterToPoint(in_raster=c2100_t, out_point_features=d2100_t)

                # Process: Raster to Point  (Raster to Point) (conversion)
                d2100_s = "memory\\d2100_s"
                with arcpy.EnvManager(outputMFlag="Disabled", outputZFlag="Disabled"):
                    arcpy.conversion.RasterToPoint(in_raster=c2100_s, out_point_features=d2100_s)

                # Process: Intersect (Intersect) (analysis)
                d2100 = "memory\\d2100_11"
                arcpy.analysis.Intersect(in_features=[[d2100_t, ""], [d2100_s, ""]], out_feature_class=d2100)

                # Call the functions within validateAndCostPath
                validate_and_cost_path_as_polyline3.process_cost_path(input_destination_data=d2100.__str__().format(**locals(),**globals())if isinstance(d2100, str) else d2100,
                                                                    input_distance_raster=cd_st,
                                                                    input_backlink_raster=bl_st,
                                                                    outputPolyline=_Value_shp)

                        
                # Delete temporary data and clean up
                data_to_delete = [
                    Buffer500,
                    d2100,
                    Buffer1km ,
                    temp2010_1km,
                    innu_2010_1km,
                    temp2010,
                    innu_2010,
                    cost2010st,
                    temp2020,
                    innu_2020,
                    cost2020st,
                    temp2030,
                    innu_2030,
                    cost2030st,
                    temp2040,
                    innu_2040,
                    cost2040st,
                    temp2050,
                    innu_2050,
                    cost2050st,
                    temp2060,
                    innu_2060,
                    cost2060st,
                    temp2070,
                    innu_2070,
                    cost2070st,
                    temp2080,
                    innu_2080,
                    cost2080st,
                    temp2090,
                    innu_2090,
                    cost2090st,
                    temp2100,
                    innu_2100,
                    cost2100st,
                    cost_st_2_,
                    cd_st,
                    bl_st,
                    c2100_t,
                    c2100_s,
                    d2100_t,
                    d2100_s
                ]

                for item in data_to_delete:
                    try:
                        if arcpy.Exists(item): 
                            arcpy.management.Delete(item)        
                        else:
                            print(f"{item} does not exist, skipping deletion.")
                    except Exception as e:
                        print(f"Error deleting {item}: {str(e)}")

            return Value, Property_2_, Property

if __name__ == '__main__':
    # Global Environment settings
    with arcpy.EnvManager(scratchWorkspace="...\\....gdb", workspace="...\\....gdb"):
        FinalModel(*argv[1:])


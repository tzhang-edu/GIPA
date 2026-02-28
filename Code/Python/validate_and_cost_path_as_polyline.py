import arcpy

def process_cost_path(input_destination_data, input_distance_raster, input_backlink_raster, outputPolyline):
    try:
        # Execute the Cost Path As Polyline tool
        arcpy.gp.CostPathAsPolyline_sa(input_destination_data, input_distance_raster, input_backlink_raster, outputPolyline)
        arcpy.AddMessage("Cost Path As Polyline completed successfully for: {}".format(outputPolyline))
    except arcpy.ExecuteError as e:
        error_message = str(e)
        # Check for specific error types
        if "ERROR 010511" in error_message:
            arcpy.AddMessage("ERROR 010511: Internal error in cost path tracing encountered. Skipping this error and continuing to next iteration...")
        elif "ERROR 010423" in error_message:
            arcpy.AddMessage("ERROR 010423 encountered. Skipping this error and continuing to next iteration...")
        elif "ERROR 010151" in error_message:
            arcpy.AddMessage("ERROR 010151: No features created by operation. Skipping this error and continuing to next iteration...")
        else:
            arcpy.AddMessage("An error occurred: " + error_message)
            return False
        return False

def main():
    # Obtain the input and output paths from the tool parameters
    input_destination_data = arcpy.GetParameterAsText(0)
    input_distance_raster = arcpy.GetParameterAsText(1)
    input_backlink_raster = arcpy.GetParameterAsText(2)
    outputPolyline = arcpy.GetParameterAsText(3)

    # Check if the input parameters are empty; if any parameter is empty, skip the process.
    if not input_destination_data or not input_distance_raster or not input_backlink_raster or not outputPolyline:
        arcpy.AddMessage("One or more input parameters are empty. Skipping this error and continuing to next iteration...")
        return

    # Assumed that input_destination_data is a set of paths to three raster datasets, separated by ";"
    input_destination_data_list = input_destination_data.split(';')
    input_distance_raster_list = input_distance_raster.split(';')
    input_backlink_raster_list = input_backlink_raster.split(';')
    outputPolyline_list = outputPolyline.split(';')
    
    for i in range(len(input_destination_data_list)):
        arcpy.AddMessage("Processing: {}".format(outputPolyline_list[i]))
        success = process_cost_path(input_destination_data_list[i], input_distance_raster_list[i], input_backlink_raster_list[i], outputPolyline_list[i])
        if not success:
            continue

if __name__ == "__main__":
    main()

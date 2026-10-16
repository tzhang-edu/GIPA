/**
 * Project: Achieving climate resistance in the global intertidal protected area system
 * Script: Global Tidal Wetland Masking and Grid Export
 * Description: This script loads the global tidal wetland dataset, applies a 30-m OSM global mask, 
 *              and systematically exports the processed data into 15°x15° grid tiles.
 */

// 1. Load the global tidal wetland change dataset
var wetlandData = ee.Image("JCU/Murray/GIC/global_tidal_wetland_change/2019");

// 2. Load the uploaded OSM global mask ImageCollection
var maskCollection = ee.ImageCollection("projects/ee-zhangting/assets/OSM_Global_Mask_30m");

// 3. Mosaic the collection into a single seamless global image
var globalMask = maskCollection.mosaic();

// 4. Apply the mask to the wetland data
var finalWetland = wetlandData.updateMask(globalMask);

// ========================================================
// 5. Loop to export 30-m high-resolution grids (15-degree tiles)
// ========================================================
var step = 15;

// Helper function to pad numbers with leading zeros for standardized naming
function padZero(num, size) {
    var s = "000" + num;
    return s.substr(s.length - size);
}

for (var lat = -90; lat < 90; lat += step) {
    for (var lon = -180; lon < 180; lon += step) {
        
        // Define bounding box for the current tile
        var xmin = lon; var xmax = lon + step;
        var ymin = lat; var ymax = lat + step;
        var tileRoi = ee.Geometry.Rectangle([xmin, ymin, xmax, ymax], null, false);
        
        // Generate standardized tile name based on coordinates
        var latStr = ymin >= 0 ? 'N' + padZero(ymin, 2) : 'S' + padZero(Math.abs(ymin), 2);
        var lonStr = xmin >= 0 ? 'E' + padZero(xmin, 3) : 'W' + padZero(Math.abs(xmin), 3);
        var tileName = "tidalflat_30m_" + latStr + lonStr;
        
        // Clip the masked data to the current tile
        var localExportImage = finalWetland.clip(tileRoi);
        
        // Create export task for Google Drive
        Export.image.toDrive({
            image: localExportImage,
            description: tileName,
            folder: 'Wetland_Final_Export',
            region: tileRoi,
            scale: 30, // Maintain 30-m resolution
            crs: 'EPSG:4326',
            maxPixels: 1e13
        });
    }
}

print("🌐 Export tasks successfully generated. Please run them in the Tasks tab!");
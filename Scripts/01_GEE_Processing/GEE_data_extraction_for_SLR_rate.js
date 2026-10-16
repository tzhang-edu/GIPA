/**
 * Project: Achieving climate resistance in the global intertidal protected area system
 * Script: Dynamic Sea Level Rise (SLR) Gridded Export (15-degree tiles)
 * Description: Dynamically loads projected SLR raster data and exports it 
 *              as GeoTIFFs in 15-degree tiles to Google Drive.
 */

// ==========================================
// 1. Parameter Settings 
// ==========================================
var sspScenario = 'ssp245';  // Options: 'ssp119', 'ssp126', 'ssp245', 'ssp370', 'ssp585'
var targetYear  = '2080';    // Options: '2020', '2030', '2040', '2050' ... '2100'

// ==========================================
// 2. Data Loading (SLR Image)
// ==========================================
var imagePath = 'IPCC/AR6/SLP/' + sspScenario + '_' + targetYear;
var slrImage = ee.Image(imagePath).select('total_rates_quantile_0_833');

// ==========================================
// 3. Loop to export 15-degree tiles
// ==========================================
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
        
        // Dynamic file name for the tile
        var tileName = "slr_" + sspScenario + "_" + targetYear + "_1km_" + latStr + lonStr;
        
        // Clip the image to the current tile
        var localExportImage = slrImage.clip(tileRoi);
        
        // Create export task for Google Drive
        Export.image.toDrive({
            image: localExportImage,
            description: tileName,
            folder: 'SLR_rates_Exports',
            region: tileRoi,
            scale: 1000,       // Export at 1km resolution
            crs: 'EPSG:4326',
            maxPixels: 1e13
        });
    }
}

print("Grid export tasks generated. Please run them in the Tasks tab!");
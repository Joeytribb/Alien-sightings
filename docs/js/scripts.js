document.addEventListener('DOMContentLoaded', function() {

    const globeContainerElement = document.getElementById('globeViz');
    const globeViewerSection = document.getElementById('globe-viewer-section');

    if (globeContainerElement && globeViewerSection) {
        fetch('data/sightings_for_globe.json')
            .then(res => {
                if (!res.ok) {
                    let errorMsg = `HTTP error! status: ${res.status}. 'data/sightings_for_globe.json' might be missing or there's an access issue.`;
                    if (res.status === 0) { // Often indicates CORS or network error when fetching locally
                        errorMsg += " If running locally, ensure you're using a local server (like VS Code's Live Server or Python's http.server) and not opening index.html directly via file:/// protocol.";
                    }
                    errorMsg += " Please run the Python script (main.py) to generate the necessary data files.";
                    throw new Error(errorMsg);
                }
                return res.json();
            })
            .then(pointsData => {
                if (!pointsData || pointsData.length === 0) {
                    console.warn("Globe data is empty. Displaying a globe without points.");
                    // Allow globe to initialize even with no points for visual consistency
                }

                const world = Globe()
                    (globeContainerElement)
                    .globeImageUrl('//unpkg.com/three-globe/example/img/earth-blue-marble.jpg')
                    .backgroundColor('rgb(255, 255, 255)') // Transparent canvas for sticky section bg
                    .pointsData(pointsData || []) // Ensure pointsData is an array
                    .pointAltitude('alt')
                    .pointRadius('radius') 
                    .pointColor('color')
                    .pointLabel(d => `Sighting (Lat: ${d.lat?.toFixed(2)}, Lng: ${d.lng?.toFixed(2)}, Dur-Scale: ${d.radius?.toFixed(3)})`)
                    .enablePointerInteraction(true);
                
                world.pointOfView({ lat: 11.2588, lng: 75.7804, altitude: 1.5 }); // Initial view: Calicut, slightly adjusted zoom

                world.controls().autoRotate = true;
                world.controls().autoRotateSpeed = 0.20; // Slower, more majestic rotation
                world.controls().enableZoom = true; 
                world.controls().zoomSpeed = 0.7;


                const resizeGlobe = () => {
                    if (globeViewerSection.clientWidth > 0 && globeViewerSection.clientHeight > 0) {
                        world.width(globeViewerSection.clientWidth);
                        world.height(globeViewerSection.clientHeight);
                    }
                };
                resizeGlobe();
                // Use ResizeObserver for more reliable resizing if available
                if (typeof ResizeObserver !== 'undefined') {
                    new ResizeObserver(resizeGlobe).observe(globeViewerSection);
                } else {
                    window.addEventListener('resize', resizeGlobe);
                }
            })
            .catch(error => {
                console.error("Error loading or initializing globe data:", error);
                if(globeContainerElement) {
                    globeContainerElement.innerHTML = `<p style="color: #ff453a; text-align: center; padding: 20px; font-weight: 500; background-color: rgba(255,255,255,0.1); border-radius: 8px;">Could not load Globe visualization. ${error.message}</p>`;
                }
            });
    } else {
        console.error("Globe container 'globeViz' or parent 'globe-viewer-section' not found in the DOM.");
    }

    const sections = document.querySelectorAll('.content-section');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
            // else { entry.target.classList.remove('visible'); } // Optional: re-animate on scroll up
        });
    }, { threshold: 0.1 }); // Trigger when 10% of the section is visible
    sections.forEach(section => { observer.observe(section); });

    function safeGetElementText(id, value, formatter = (val) => val?.toLocaleString() || 'N/A') {
        const el = document.getElementById(id);
        if (el) {
            el.textContent = (value === null || value === undefined || Number.isNaN(value)) ? 'N/A' : formatter(value);
        } else {
            console.warn(`Element with ID '${id}' not found.`);
        }
    }
    
    function capitalizeFirstLetter(string) {
        if (!string || typeof string !== 'string') return 'N/A';
        return string.charAt(0).toUpperCase() + string.slice(1);
    }


    fetch('data/eda_summary.json') 
        .then(res => {
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status} - 'data/eda_summary.json' missing or unreadable. Please run the Python script (main.py).`);
            return res.json();
        })
        .then(summary => {
            if (Object.keys(summary).length === 0) {
                 console.warn("EDA summary data is empty. Displaying N/A for all values.");
            }

            safeGetElementText('total-sightings', summary.total_sightings);
            safeGetElementText('peak-hour', summary.peak_hour_readable);
            safeGetElementText('peak-hour-dominant-shape', summary.peak_hour_dominant_shape, val => capitalizeFirstLetter(val));
            safeGetElementText('peak-month', summary.peak_month);
            safeGetElementText('most-common-shape', summary.most_common_shape, val => capitalizeFirstLetter(val));
            safeGetElementText('second-most-common-shape', summary.second_most_common_shape, val => capitalizeFirstLetter(val));
            
            const durationsByShape = summary.median_durations_by_top_shapes || {};
            const shapeDurationsArray = Object.entries(durationsByShape)
                                          .filter(([_, duration]) => duration !== null && duration !== undefined && !Number.isNaN(duration))
                                          .sort(([,a],[,b]) => a - b);

            if (shapeDurationsArray.length > 0) {
                const shortest = shapeDurationsArray[0];
                const longest = shapeDurationsArray[shapeDurationsArray.length-1];

                safeGetElementText('shape-shortest-duration', shortest[0], val => capitalizeFirstLetter(val));
                safeGetElementText('median-duration-shortest-shape', shortest[1], val => parseFloat(val).toFixed(0));
                safeGetElementText('text-shape-shortest', shortest[0], val => capitalizeFirstLetter(val));
                safeGetElementText('text-median-shortest', shortest[1], val => parseFloat(val).toFixed(0));
                
                safeGetElementText('shape-longest-duration', longest[0], val => capitalizeFirstLetter(val));
                safeGetElementText('median-duration-longest-shape', longest[1], val => parseFloat(val).toFixed(0));
                safeGetElementText('text-shape-longest', longest[0], val => capitalizeFirstLetter(val));
                safeGetElementText('text-median-longest', longest[1], val => parseFloat(val).toFixed(0));
            } else {
                ['shape-shortest-duration', 'median-duration-shortest-shape', 'text-shape-shortest', 'text-median-shortest', 
                 'shape-longest-duration', 'median-duration-longest-shape', 'text-shape-longest', 'text-median-longest'].forEach(id => safeGetElementText(id, null));
            }
            
            safeGetElementText('median-duration-night', summary.median_duration_night_seconds, val => parseFloat(val).toFixed(0));
            safeGetElementText('median-duration-day', summary.median_duration_day_seconds, val => parseFloat(val).toFixed(0));

            safeGetElementText('proportion-over-5-min', summary.proportion_over_5_min_percent, val => parseFloat(val).toFixed(1));
            safeGetElementText('proportion-over-1-hour', summary.proportion_over_1_hour_percent, val => parseFloat(val).toFixed(1));

            safeGetElementText('median-duration-overall', summary.median_duration_seconds_overall, val => parseFloat(val).toFixed(0));
            safeGetElementText('peak-year', summary.peak_year_of_reports);

            // For additional text details:
            safeGetElementText('peak-hour-detail-time', summary.peak_hour_readable);
            safeGetElementText('peak-hour-detail-shapes', summary.top_shapes_in_peak_hour_summary, val => val || 'Not enough data');


            // --- Chart.js Configuration ---
            Chart.defaults.color = '#333'; 
            Chart.defaults.borderColor = 'rgba(0,0,0,0.05)';
            Chart.defaults.font.family = "'Roboto', sans-serif";
            Chart.defaults.plugins.legend.position = 'bottom';
            Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(0,0,0,0.7)';
            Chart.defaults.plugins.tooltip.titleFont = { weight: 'bold', size: 14 };
            Chart.defaults.plugins.tooltip.bodyFont = { size: 12 };
            Chart.defaults.responsive = true;
            Chart.defaults.maintainAspectRatio = false; // Crucial for fitting charts in fixed-height containers
            
            const chartOptions = (isIndexAxisY = false) => ({
                scales: {
                    y: { 
                        beginAtZero: true, 
                        grid: { color: Chart.defaults.borderColor, drawOnChartArea: !isIndexAxisY },
                        ticks: { color: '#555', font: {size: 10} } 
                    },
                    x: { 
                        grid: { color: Chart.defaults.borderColor, drawOnChartArea: isIndexAxisY },
                        ticks: { color: '#555', font: {size: 10} }
                    }
                },
                plugins: { 
                    legend: { labels: { color: '#333', font: {size: 12} } }
                },
                ...(isIndexAxisY && { indexAxis: 'y' }) // Conditionally add indexAxis
            });

            const accentColors = {
                blue: { solid: 'rgb(0, 122, 255)', alpha: 'rgba(0, 122, 255, 0.6)' },
                red: { solid: 'rgb(255, 59, 48)', alpha: 'rgba(255, 59, 48, 0.6)' },
                green: { solid: 'rgb(52, 199, 89)', alpha: 'rgba(52, 199, 89, 0.6)' },
                orange: { solid: 'rgb(255, 149, 0)', alpha: 'rgba(255, 149, 0, 0.6)'}
            };
            
            const shapeChartPalette = [
                'rgba(0, 122, 255, 0.7)', 'rgba(52, 199, 89, 0.7)', 'rgba(255, 149, 0, 0.7)', 
                'rgba(88, 86, 214, 0.7)', 'rgba(255, 45, 85, 0.7)', 'rgba(175, 82, 222, 0.7)', 
                'rgba(255, 204, 0, 0.7)', 'rgba(10, 132, 255, 0.7)', 'rgba(48, 209, 88, 0.7)', 
                'rgba(255, 159, 10, 0.7)' 
            ].map(color => ({
                solid: color.replace('0.7', '1'),
                alpha: color
            }));


            // Year Chart
            if (summary.sightings_by_year && Object.keys(summary.sightings_by_year).length > 0) {
                const yearData = Object.entries(summary.sightings_by_year)
                                   .map(([year, count]) => ({ year: parseInt(year), count }))
                                   .sort((a, b) => a.year - b.year);
                const recentYearsData = yearData.length > 30 ? yearData.slice(-30) : yearData; 
                new Chart(document.getElementById('yearChart'), {
                    type: 'line',
                    data: { labels: recentYearsData.map(d => d.year.toString()), datasets: [{ label: 'Sightings', data: recentYearsData.map(d => d.count), borderColor: accentColors.blue.solid, backgroundColor: accentColors.blue.alpha, tension: 0.3, fill: true }] },
                    options: chartOptions()
                });
            } else { document.getElementById('yearChart').parentElement.innerHTML = "<p class='chart-nodata'>Year data not available.</p>"; }

            // Month Chart
            if (summary.sightings_by_month && Object.keys(summary.sightings_by_month).length > 0) {
                const monthOrder = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
                const monthLabels = monthOrder.filter(month => summary.sightings_by_month[month] !== undefined);
                const monthCounts = monthLabels.map(month => summary.sightings_by_month[month]);
                new Chart(document.getElementById('monthChart'), {
                    type: 'bar',
                    data: { labels: monthLabels, datasets: [{ label: 'Sightings', data: monthCounts, backgroundColor: accentColors.red.alpha, borderColor: accentColors.red.solid, borderWidth: 1 }] },
                    options: chartOptions()
                });
            } else { document.getElementById('monthChart').parentElement.innerHTML = "<p class='chart-nodata'>Month data not available.</p>"; }

            // Hour Chart
            if (summary.sightings_by_hour && Object.keys(summary.sightings_by_hour).length > 0) {
                 const hourLabels = Object.keys(summary.sightings_by_hour).map(h => parseInt(h)).sort((a,b)=>a-b).map(h => `${h.toString().padStart(2, '0')}:00`);
                 const hourCounts = Object.keys(summary.sightings_by_hour).map(h => parseInt(h)).sort((a,b)=>a-b).map(h => summary.sightings_by_hour[String(h)]); // Key is string in JSON
                new Chart(document.getElementById('hourChart'), {
                    type: 'line',
                    data: { labels: hourLabels, datasets: [{ label: 'Sightings', data: hourCounts, borderColor: accentColors.green.solid, backgroundColor: accentColors.green.alpha, tension: 0.3, fill: true }] },
                    options: chartOptions()
                });
            } else { document.getElementById('hourChart').parentElement.innerHTML = "<p class='chart-nodata'>Hour data not available.</p>"; }

            // Country Chart
            if (summary.top_countries && Object.keys(summary.top_countries).length > 0) {
                new Chart(document.getElementById('countryChart'), {
                    type: 'bar', data: { labels: Object.keys(summary.top_countries).map(c => c.toUpperCase()), datasets: [{ label: 'Sightings', data: Object.values(summary.top_countries), backgroundColor: accentColors.red.alpha, borderColor: accentColors.red.solid, borderWidth: 1 }] },
                    options: chartOptions(true) // isIndexAxisY = true
                });
            } else { document.getElementById('countryChart').parentElement.innerHTML = "<p class='chart-nodata'>Country data not available.</p>"; }

            // State Chart
            if (summary.top_states_us && Object.keys(summary.top_states_us).length > 0) {
                 new Chart(document.getElementById('stateChart'), {
                    type: 'bar', data: { labels: Object.keys(summary.top_states_us), datasets: [{ label: 'Sightings', data: Object.values(summary.top_states_us), backgroundColor: accentColors.blue.alpha, borderColor: accentColors.blue.solid, borderWidth: 1 }] },
                    options: chartOptions(true)
                });
            } else { document.getElementById('stateChart').parentElement.innerHTML = "<p class='chart-nodata'>US State data not available.</p>"; }

            // Shape Chart
            if (summary.top_shapes && Object.keys(summary.top_shapes).length > 0) {
                new Chart(document.getElementById('shapeChart'), {
                    type: 'bar',
                    data: { 
                        labels: Object.keys(summary.top_shapes).map(s => capitalizeFirstLetter(s)),
                        datasets: [{ 
                            label: 'Sightings', 
                            data: Object.values(summary.top_shapes), 
                            backgroundColor: shapeChartPalette.map(p => p.alpha),
                            borderColor: shapeChartPalette.map(p => p.solid),
                            borderWidth: 1 
                        }] 
                    },
                    options: {...chartOptions(true), plugins: {...chartOptions(true).plugins, legend: {display: false} }}
                });
            } else { document.getElementById('shapeChart').parentElement.innerHTML = "<p class='chart-nodata'>Shape data not available.</p>"; }
        })
        .catch(error => {
            console.error("Error loading or processing EDA summary:", error);
            const introSection = document.getElementById('introduction');
            if (introSection) {
                 introSection.innerHTML = `<div class="content-section visible" style="background-color: #ffebee; border-left-color: #f44336;">
                    <h2 style="color: #d32f2f;">Critical Data Error</h2>
                    <p style="color: #b71c1c; font-weight: 500;">Could not load or process the EDA summary data ('data/eda_summary.json'). This is essential for the page to function correctly.</p>
                    <p style="color: #b71c1c;"><strong>Please ensure the Python script (main.py) has been run successfully and generated the data files.</strong> Check the script's console output for errors.</p>
                    <p style="color: #b71c1c; font-size: 0.9em;">Error details: ${error.message}</p>
                    </div>` + introSection.innerHTML; // Prepend error
            }
            // Display error messages in chart containers
            ['yearChart', 'monthChart', 'hourChart', 'countryChart', 'stateChart', 'shapeChart'].forEach(id => {
                const chartElParent = document.getElementById(id)?.parentElement;
                if(chartElParent) chartElParent.innerHTML = `<p class='chart-nodata error'>Chart data unavailable. ${error.message.includes("eda_summary.json") ? "Failed to load summary." : "Error processing chart data."}</p>`;
            });
        });
});
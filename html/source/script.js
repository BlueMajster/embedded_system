const ctx = document.getElementById('temphumChart');

const TempHum = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label: 'Temperature',
        data: [],
        borderColor: 'rgba(255, 99, 132, 1)',
        borderWidth: 2,
        pointRadius: 1,
        tension: 0.4,
        yAxisID: 'y'
      },
      {
        label: 'Humidity',
        data: [],
        borderColor: 'rgba(54, 162, 235, 1)',
        borderWidth: 2,
        pointRadius: 1,
        tension: 0.4,
        yAxisID: 'y1'
      }]
    },
    plugins: [{
      id: 'horizontalTitles',
      afterDraw: (chart) => {
          const { ctx, scales: { y, y1 } } = chart;
          ctx.save();
                        ctx.font = '14px "Arial", cursive';
          if (y) {
              ctx.fillStyle = 'rgba(255, 99, 132, 1)';
              ctx.textAlign = 'left';
              ctx.fillText('℃', 0, 20);
          }

          if (y1) {
              ctx.fillStyle = 'rgba(54, 162, 235, 1)';
              ctx.textAlign = 'right';
              ctx.fillText('%', chart.width, 20);
          }
          ctx.restore();
      }
    }],
    options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        layout: {
            padding: { top: 13 }
        },
        interaction: {
            mode: 'index',
            intersect: false,
        },
        plugins: {
            legend: {
                display: true,
                position: 'top',
                align: 'center',
                labels: {
                    // usePointStyle: true,
                    boxWidth: 25,
                    boxHeight: 1.5
                }
            }
        },
        scales: {
          x: {
              ticks: {
                  autoSkip: true,
                  maxTicksLimit: 5,
                  maxRotation: 0,
                  minRotation: 0,
                  align: 'center',
                  labelOffset: 45
              }
          },
        y: {
          type: 'linear',
          display: true,
          position: 'left',
          beginAtZero: false,
          grace: 2,
          title: {
            display: false,
            // text: '℃',
            // align: 'end',
            // rotation: 0,
            // font: {
            //   weight: 'bold'
            // }
          }
        },
        y1: {
          type: 'linear',
          display: true,
          position: 'right',
          beginAtZero: false,
          grace: 2,
          title: {
            display: false,
            // text: '%',
            // align: 'end',
            // rotation: 0,
            // font: {
            //   weight: 'bold'
            // }
          },
          grid: {
            drawOnChartArea: false
          }
        }
      }
    }
  });
const ctxPressure = document.getElementById('pressureChart');

const PressureChart = new Chart(ctxPressure, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Pressure (hPa)',
            data: [],
            borderColor: 'rgba(153, 102, 255, 1)',
            backgroundColor: 'rgba(153, 102, 255, 0.2)',
            borderWidth: 2,
            pointRadius: 1,
            tension: 0.4,
            fill: true // wypełnienie pod wykresem
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        interaction: {
            mode: 'index',
            intersect: false,
        },
        scales: {
            x: {
                ticks: {
                    autoSkip: true,
                    maxTicksLimit: 5,
                    maxRotation: 0,
                    minRotation: 0,
                    align: 'center',
                    labelOffset: 40
                }
            },
            y: {
                beginAtZero: false,
                grace: 2,
                // min: 980,
                // max: 1020,
                title: {
                    display: false,
                    // text: 'hPa',
                    // align: 'end',
                    // rotation: 0,
                    // font: {
                    //   weight: 'bold'
                    // }
                }
            }
        }
    }
});

const audio = new Audio('../source/sounds/police-60.mp3');
const audio2 = new Audio('../source/sounds/police-60-reverse.mp3');
audio.volume = 0.2;
audio2.volume = 0.2;
document.getElementById('policeman').onclick = function() {
    const alkoBox = document.querySelector('.alko-info');
    
    if(alkoBox.style.display == 'flex') {
      alkoBox.style.display = 'none';
      audio2.play();
      setTimeout(() => {
        audio2.pause();
        audio2.currentTime = 0;
      }, 5000);
    }
    else {
      alkoBox.style.display = 'flex';
      audio.play();
      setTimeout(() => {
        audio.pause();
        audio.currentTime = 0;
      }, 5000);
    }
}

function loadHistory() {
    fetch('/history')
    .then(Response => Response.json())
    .then(data => {
        if (data.length > 0) {
            data.forEach(record => {
                TempHum.data.labels.push(record.time);
                TempHum.data.datasets[0].data.push(record.temp);
                TempHum.data.datasets[1].data.push(record.hum);

                PressureChart.data.labels.push(record.time);
                PressureChart.data.datasets[0].data.push(record.pres);
            });
            TempHum.update();
            PressureChart.update();
        }
    })
    .catch(error => {
        console.error('Error fetching history data:', error);
    });
}
lastUpdate = 0;
const UPDATE_INTERVAL = 600000; // 10 minutes
function updateData() {
    fetch('/data')
    .then(Response => Response.json())
    .then(data => {
        document.getElementById('temp').innerText = data.temp + ' ℃';
        document.getElementById('hum').innerText = data.hum + ' %';
        document.getElementById('pres').innerText = data.pres + ' hPa';
        if(data.light < 980) {
            document.getElementById('light2').innerText = 'Bright';
        }
        else {
            document.getElementById('light2').innerText = 'Dark';
        }
        // document.getElementById('light2').innerText = data.light;
        if(data.proximity == 1) {
          document.getElementById('ir-door').innerText = 'Open';
        }
        else {
          document.getElementById('ir-door').innerText = 'Closed';
        }
        if(data.motion == 1) {
          document.getElementById('pir-sensor').innerText = 'Motion detected';
        }
        else {
          document.getElementById('pir-sensor').innerText = 'No motion';
        }
        if(data.alcohol > 950) {
          document.getElementById('alcohol-value').innerText = "Drunk";
          document.getElementById('alcohol-value').style.color = "#ff6b6b";
        }
        else {
          document.getElementById('alcohol-value').innerText = "Sober";
          document.getElementById('alcohol-value').style.color = "#6bff77";
        }

        const detectedPeople = data.people_list || [];
        document.getElementById("people-count").innerText = "Current Occupancy: " + detectedPeople.length;
        if (detectedPeople.length > 0) {
            document.getElementById("detected-names").innerText = "Identified: " + detectedPeople.join(", ");
        }
        else {
            document.getElementById("detected-names").innerText = "Room Empty";
        }

        const now2 = Date.now();
        if (now2 - lastUpdate > UPDATE_INTERVAL) {
          const now = new Date();
          const timeLabel = now.getDate() + "-" + (now.getMonth() + 1) + " " + now.getHours() + ":" + now.getMinutes();
          // const timeNow = new Date().toLocaleTimeString();

          TempHum.data.labels.push(timeLabel);
          TempHum.data.datasets[0].data.push(data.temp);
          TempHum.data.datasets[1].data.push(data.hum);

          PressureChart.data.labels.push(timeLabel);
          PressureChart.data.datasets[0].data.push(data.pres);

          if (TempHum.data.labels.length > 3000) {
              TempHum.data.labels.shift();
              TempHum.data.datasets[0].data.shift();
              TempHum.data.datasets[1].data.shift();
          }
          if (PressureChart.data.labels.length > 3000) {
              PressureChart.data.labels.shift();
              PressureChart.data.datasets[0].data.shift();
          }

          PressureChart.update();
          TempHum.update();
          lastUpdate = now2;
        }
    });
}
loadHistory();
setInterval(updateData, 500);

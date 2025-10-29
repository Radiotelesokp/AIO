let autoScroll = true;
        let isConnected = false;
        let updateInterval;
        let selectedObject = null;

        // API Base URL
        const API_BASE = '';

        // Initialize
        document.addEventListener('DOMContentLoaded', function() {
            log('Interfejs webowy uruchomiony');
            log('Sprawdzam połączenie z API...');

            refreshPorts();
            checkApiConnection();
            startStatusUpdates();
            updateTime();
            setInterval(updateTime, 1000);

            // Keyboard shortcut for emergency stop
            document.addEventListener('keydown', function(e) {
                if (e.code === 'Space') {
                    e.preventDefault();
                    emergencyStop();
                }
            });

            // Inicjalne wyłączenie wszystkich kontrolek do momentu połączenia
            updateControlsState();
        });

        // Funkcja aktualizująca stan kontrolek w zależności od stanu połączenia
        function updateControlsState() {
            const controlButtons = document.querySelectorAll('.card:not(:first-child) button');
            const controlInputs = document.querySelectorAll('.card:not(:first-child) input, .card:not(:first-child) select');
            const advancedToggle = document.querySelector('.advanced-options-toggle');
            const objectButtons = document.querySelectorAll('.object-button');

            // Ustaw stan aktywności dla wszystkich kontrolek poza panelem połączenia
            controlButtons.forEach(button => {
                button.disabled = !isConnected;
            });

            controlInputs.forEach(input => {
                input.disabled = !isConnected;
            });

            // Blokowanie przycisków obiektów astronomicznych
            objectButtons.forEach(button => {
                if (!isConnected) {
                    // Wyłącz możliwość klikania na przyciski
                    button.style.pointerEvents = 'none';
                    button.style.opacity = '0.5';
                    button.classList.remove('selected');
                } else {
                    // Włącz możliwość klikania
                    button.style.pointerEvents = 'auto';
                    button.style.opacity = '1';
                }
            });

            // Opcje zaawansowane też blokujemy
            if (advancedToggle) {
                advancedToggle.disabled = !isConnected;

                // Jeśli nie jesteśmy połączeni, ukryj panel opcji zaawansowanych
                if (!isConnected && document.getElementById('advancedOptionsContainer').style.display !== 'none') {
                    toggleAdvancedOptions(advancedToggle);
                }
            }

            // Resetuj wybrany obiekt jeśli rozłączono
            if (!isConnected) {
                selectedObject = null;
                document.getElementById('objectNameInput').value = '';
                document.getElementById('objectInfo').textContent = '';
            }
        }



        async function apiCall(endpoint, method = 'GET', data = null) {
            try {
                const config = {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json',
                    }
                };

                if (data) {
                    config.body = JSON.stringify(data);
                }

                const response = await fetch(API_BASE + endpoint, config);

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                return await response.json();
            } catch (error) {
                log(`Błąd API: ${error.message}`, 'error');
                throw error;
            }
        }

        async function checkApiConnection() {
            try {
                await apiCall('/');
                log('Połączenie z API OK', 'success');
            } catch (error) {
                log('Błąd połączenia z API', 'error');
            }
        }

        async function refreshPorts() {
            try {
                const response = await apiCall('/ports');
                const portSelect = document.getElementById('portSelect');

                // Clear existing options except predefined ones
                const predefinedPorts = [
                    { value: '', text: 'Auto-detect' },
                    { value: '/dev/tty.usbserial-A10PDNT7', text: '/dev/tty.usbserial-A10PDNT7' },
                    { value: '/dev/ttyUSB0', text: '/dev/ttyUSB0' },
                    { value: 'COM10', text: 'COM10' }
                ];

                portSelect.innerHTML = '';
                predefinedPorts.forEach(port => {
                    const option = document.createElement('option');
                    option.value = port.value;
                    option.textContent = port.text;
                    portSelect.appendChild(option);
                });

                // Add any additional detected ports
                response.ports.forEach(port => {
                    if (!predefinedPorts.some(p => p.value === port)) {
                        const option = document.createElement('option');
                        option.value = port;
                        option.textContent = port;
                        portSelect.appendChild(option);
                    }
                });

                log('Porty odświeżone', 'success');
            } catch (error) {
                log('Błąd odświeżania portów', 'error');
            }
        }

        function selectAstronomicalObject(name, type) {
            // Remove selection from all buttons
            document.querySelectorAll('.object-button').forEach(btn => {
                btn.classList.remove('selected');
            });

            // Add selection to clicked button
            event.target.classList.add('selected');

            // Update input fields
            document.getElementById('objectNameInput').value = name;
            document.getElementById('objectTypeSelect').value = type;

            selectedObject = { name, type };
            log(`Wybrano obiekt: ${name} (${type})`);

            // Update object info
            updateObjectInfo(name, type);
        }

        function updateObjectInfo(name, type) {
            const infoElement = document.getElementById('objectInfo');
            let info = '';

            switch(type) {
                case 'SUN':
                    info = 'Słońce - główna gwiazda Układu Słonecznego';
                    break;
                case 'MOON':
                    info = 'Księżyc - naturalny satelita Ziemi';
                    break;
                case 'PLANET':
                    const planetInfo = {
                        'mercury': 'Merkury - najmniejsza planeta Układu Słonecznego',
                        'venus': 'Wenus - najgorętszą planetą Układu Słonecznego',
                        'mars': 'Mars - "Czerwona Planeta"',
                        'jupiter': 'Jowisz - największa planeta Układu Słonecznego',
                        'saturn': 'Saturn - planeta z pierścieniami',
                        'uranus': 'Uran - lodowa planeta',
                        'neptune': 'Neptun - najbardziej odległa planeta'
                    };
                    info = planetInfo[name.toLowerCase()] || `${name} - planeta`;
                    break;
                case 'STAR':
                    const starInfo = {
                        'vega': 'Vega - najjaśniejsza gwiazda w Lirze',
                        'sirius': 'Syriusz - najjaśniejsza gwiazda na niebie',
                        'polaris': 'Gwiazda Polarna - wskazuje kierunek północy',
                        'betelgeuse': 'Betelgeza - czerwony nadolbrzym w Orionie',
                        'rigel': 'Rigel - niebieski nadolbrzym w Orionie',
                        'altair': 'Altair - gwiazda w Orle',
                        'deneb': 'Deneb - bardzo jasna gwiazda w Łabędziu',
                        'antares': 'Antares - czerwony nadolbrzym w Skorpionie'
                    };
                    info = starInfo[name.toLowerCase()] || `${name} - gwiazda`;
                    break;
                default:
                    info = `${name} - obiekt astronomiczny`;
            }

            infoElement.textContent = info;
        }

        async function getObjectPosition() {
            if (!selectedObject) {
                log('Nie wybrano obiektu astronomicznego', 'error');
                return;
            }

            try {
                // Automatycznie ustaw lokalizację jeśli nie jest ustawiona
                await ensureObserverLocationSet();

                const response = await apiCall(`/astronomical/position/${selectedObject.name}`);
                log(`Pozycja ${selectedObject.name}: Az ${response.azimuth.toFixed(1)}°, El ${response.elevation.toFixed(1)}°`);

                // Optionally update position inputs
                document.getElementById('azimuthInput').value = response.azimuth.toFixed(1);
                document.getElementById('elevationInput').value = response.elevation.toFixed(1);

            } catch (error) {
                log(`Błąd pobierania pozycji obiektu ${selectedObject.name}`, 'error');
            }
        }

        async function connectAntenna() {
            try {
                const port = document.getElementById('portSelect').value;
                const useSimulator = document.getElementById('simulatorMode').checked;

                log(useSimulator ? 'Łączę z symulatorem...' : 'Łączę ze sprzętem...');

                const config = {
                    port: port || null,
                    use_simulator: useSimulator
                };

                await apiCall('/connect', 'POST', config);
                isConnected = true;
                updateConnectionStatus();
                log('Połączenie nawiązane', 'success');
                
                // Wczytaj kalibrację po połączeniu
                setTimeout(() => {
                    loadCalibrationSettings();
                }, 1000);

            } catch (error) {
                log(`Błąd połączenia z ${document.getElementById('simulatorMode').checked ? 'symulatorem' : 'sprzętem'}: ${error.message}`, 'error');
                isConnected = false;
                updateConnectionStatus();
            }
        }

        async function disconnectAntenna() {
            try {
                await apiCall('/disconnect', 'POST');
                isConnected = false;
                updateConnectionStatus();
                log('Rozłączono', 'success');
            } catch (error) {
                log('Błąd rozłączania', 'error');
            }
        }

        async function moveToPosition() {
            try {
                const azimuth = parseFloat(document.getElementById('azimuthInput').value);
                const elevation = parseFloat(document.getElementById('elevationInput').value);

                if (isNaN(azimuth) || isNaN(elevation)) {
                    log('Nieprawidłowe wartości pozycji', 'error');
                    return;
                }

                const position = { azimuth, elevation };
                await apiCall('/position', 'POST', position);
                log(`Poruszam do pozycji: Az ${azimuth}°, El ${elevation}°`);

            } catch (error) {
                log('Błąd ustawiania pozycji', 'error');
            }
        }

        async function getCurrentPosition() {
            try {
                const position = await apiCall('/position');
                document.getElementById('azimuthInput').value = position.azimuth.toFixed(1);
                document.getElementById('elevationInput').value = position.elevation.toFixed(1);
                log(`Aktualna pozycja: Az ${position.azimuth.toFixed(1)}°, El ${position.elevation.toFixed(1)}°`);
            } catch (error) {
                log('Błąd odczytu pozycji', 'error');
            }
        }

        async function stopAntenna() {
            try {
                await apiCall('/stop', 'POST');
                log('ZATRZYMUJĘ ANTENĘ!', 'warning');
            } catch (error) {
                log(`Błąd zatrzymania: ${error.message}`, 'error');
            }
        }

        async function setObserverLocation() {
            try {
                const location = {
                    latitude: parseFloat(document.getElementById('latitudeInput').value),
                    longitude: parseFloat(document.getElementById('longitudeInput').value),
                    elevation: parseFloat(document.getElementById('elevationObsInput').value),
                    name: document.getElementById('locationNameInput').value
                };

                await apiCall('/observer', 'POST', location);
                log(`Ustawiono lokalizację obserwatora: ${location.name}`, 'success');

            } catch (error) {
                log('Błąd ustawiania lokalizacji', 'error');
            }
        }

        async function getObserverLocation() {
            try {
                await ensureObserverLocationSet();
                const location = await apiCall('/observer');
                document.getElementById('latitudeInput').value = location.latitude;
                document.getElementById('longitudeInput').value = location.longitude;
                document.getElementById('elevationObsInput').value = location.elevation;
                document.getElementById('locationNameInput').value = location.name;
                log(`Pobrano lokalizację: ${location.name}`, 'success');
            } catch (error) {
                log('Błąd pobierania lokalizacji', 'error');
            }
        }

        async function startTracking() {
            try {
                // Automatycznie ustaw lokalizację jeśli nie jest ustawiona
                await ensureObserverLocationSet();

                const objectName = document.getElementById('objectNameInput').value.trim();
                const objectType = document.getElementById('objectTypeSelect').value;

                if (!objectName) {
                    log('Wybierz obiekt do śledzenia', 'error');
                    return;
                }

                // Użyj nowego endpointu /start_tracking z TrackingConfigModel
                const trackingConfig = {
                    object_name: objectName,
                    object_type: objectType,
                    update_interval: 1.0
                };                const response = await apiCall('/start_tracking', 'POST', trackingConfig);
                log(`Rozpoczęto ciągłe śledzenie: ${objectName}`, 'success');

            } catch (error) {
                log('Błąd rozpoczynania śledzenia', 'error');
            }
        }

        async function stopTracking() {
            try {
                await apiCall('/stop_tracking', 'POST');
                log('Zatrzymano śledzenie', 'success');
            } catch (error) {
                log('Błąd zatrzymywania śledzenia', 'error');
            }
        }


        function updateConnectionStatus() {
            const statusElement = document.getElementById('connectionStatus');
            statusElement.textContent = isConnected ? 'Połączony' : 'Rozłączony';
            statusElement.className = isConnected ? 'connected' : 'disconnected';

            // Aktualizuj stan kontrolek gdy zmienia się stan połączenia
            updateControlsState();
        }

        async function updateStatus() {
            try {
                const status = await apiCall('/status');

                // Update connection status
                isConnected = status.connected;
                updateConnectionStatus();

                // Update position
                if (status.current_position) {
                    document.getElementById('azimuthValue').textContent =
                        status.current_position.azimuth.toFixed(1) + '°';
                    document.getElementById('elevationValue').textContent =
                        status.current_position.elevation.toFixed(1) + '°';
                } else {
                    document.getElementById('azimuthValue').textContent = '---°';
                    document.getElementById('elevationValue').textContent = '---°';
                }

                // Update moving status
                document.getElementById('movingStatus').textContent =
                    status.is_moving ? 'W ruchu' : 'Zatrzymany';

                // Update port status
                document.getElementById('portStatus').textContent = status.port || '---';


            } catch (error) {
                // Błąd zostanie zalogowany przez apiCall
            }
        }

        function startStatusUpdates() {
            updateInterval = setInterval(updateStatus, 2000);
        }

        // Cleanup on page unload
        window.addEventListener('beforeunload', function() {
            if (updateInterval) {
                clearInterval(updateInterval);
            }
        });

        async function moveToObject() {
            if (!selectedObject) {
                log('Nie wybrano obiektu astronomicznego', 'error');
                return;
            }

            try {
                // Automatycznie ustaw lokalizację jeśli nie jest ustawiona
                await ensureObserverLocationSet();

                // Najpierw pobierz pozycję obiektu
                const response = await apiCall(`/astronomical/position/${selectedObject.name}`);

                if (!response.is_visible) {
                    log(`Obiekt ${selectedObject.name} nie jest widoczny (elewacja: ${response.elevation.toFixed(1)}°)`, 'warning');
                    const proceed = confirm(`Obiekt ${selectedObject.name} jest pod horyzontem. Czy kontynuować?`);
                    if (!proceed) return;
                }

                log(`Przesuwam do obiektu ${selectedObject.name}: Az ${response.azimuth.toFixed(1)}°, El ${response.elevation.toFixed(1)}°`);

                // Przesuń antenę do pozycji obiektu
                const position = {
                    azimuth: response.azimuth,
                    elevation: response.elevation
                };
                await apiCall('/position', 'POST', position);

                // Aktualizuj pola pozycji
                document.getElementById('azimuthInput').value = response.azimuth.toFixed(1);
                document.getElementById('elevationInput').value = response.elevation.toFixed(1);

                log(`Poruszam do pozycji obiektu ${selectedObject.name}`, 'success');

            } catch (error) {
                log(`Błąd przesuwania do obiektu ${selectedObject.name}: ${error.message}`, 'error');
            }
        }

        async function ensureObserverLocationSet() {
            try {
                // Sprawdź czy lokalizacja jest już ustawiona
                await apiCall('/observer');
                return; // Lokalizacja już ustawiona
            } catch (error) {
                if (error.message.includes('404')) {
                    // Lokalizacja nie jest ustawiona, ustaw domyślną
                    log('Ustawiam domyślną lokalizację obserwatora...', 'warning');

                    const defaultLocation = {
                        latitude: parseFloat(document.getElementById('latitudeInput').value) || 52.4064,
                        longitude: parseFloat(document.getElementById('longitudeInput').value) || 16.9252,
                        elevation: parseFloat(document.getElementById('elevationObsInput').value) || 75,
                        name: document.getElementById('locationNameInput').value || 'Poznań'
                    };

                    await apiCall('/observer', 'POST', defaultLocation);
                    log(`Automatycznie ustawiono lokalizację: ${defaultLocation.name}`, 'success');
                } else {
                    throw error; // Inny błąd
                }
            }
        }

        function setPresetPosition(azimuth, elevation) {
            document.getElementById('azimuthInput').value = azimuth;
            document.getElementById('elevationInput').value = elevation;
            log(`Ustawiono zapamiętaną pozycję: Az ${azimuth}°, El ${elevation}°`);
        }

        async function moveToPresetPosition() {
            const azimuth = parseFloat(document.getElementById('azimuthInput').value);
            const elevation = parseFloat(document.getElementById('elevationInput').value);

            if (isNaN(azimuth) || isNaN(elevation)) {
                log('Nieprawidłowe wartości pozycji', 'error');
                return;
            }

            try {
                // Automatycznie ustaw lokalizację jeśli nie jest ustawiona
                await ensureObserverLocationSet();

                const response = await apiCall('/position', 'POST', { azimuth, elevation });
                log(`Przesunięto do pozycji: Az ${azimuth}°, El ${elevation}°`, 'success');
            } catch (error) {
                log('Błąd przesuwania do pozycji', 'error');
            }
        }

        async function calibrateNorth() {
            try {
                const invertAzimuth = document.getElementById('invertAzimuth').checked;
                const response = await apiCall('/calibrate_azimuth', 'POST', {
                    current_azimuth: null,
                    invert_azimuth: invertAzimuth,
                    save_to_file: true
                });
                log(`Kalibracja północy zakończona. Offset: ${response.azimuth_offset.toFixed(2)}°`, 'success');
            } catch (error) {
                log('Błąd kalibracji północy: ' + error.message, 'error');
            }
        }

        async function resetCalibration() {
            try {
                await apiCall('/reset_calibration', 'POST');
                log('Kalibracja zresetowana do wartości domyślnych', 'success');
                // Zaktualizuj interfejs
                await loadCalibrationSettings();
            } catch (error) {
                log('Błąd resetowania kalibracji: ' + error.message, 'error');
            }
        }

        async function applyAxisSettings() {
            const invertAzimuth = document.getElementById('invertAzimuth').checked;
            const invertElevation = document.getElementById('invertElevation').checked;
            const azimuthOffset = parseFloat(document.getElementById('azimuthOffset').value) || 0;
            const elevationOffset = parseFloat(document.getElementById('elevationOffset').value) || 0;

            try {
                await apiCall('/calibration', 'POST', {
                    azimuth_inverted: invertAzimuth,
                    azimuth_offset: azimuthOffset,
                    elevation_inverted: invertElevation,
                    elevation_offset: elevationOffset
                });
                
                log('Zastosowano ustawienia kalibracji', 'success');
                
                // Zapisz ustawienia w lokalnej pamięci
                localStorage.setItem('invertAzimuth', invertAzimuth);
                localStorage.setItem('invertElevation', invertElevation);
                localStorage.setItem('azimuthOffset', azimuthOffset);
                localStorage.setItem('elevationOffset', elevationOffset);
                
            } catch (error) {
                log('Błąd ustawiania kalibracji: ' + error.message, 'error');
            }
        }

        async function loadCalibrationSettings() {
            try {
                const calibration = await apiCall('/calibration', 'GET');
                
                document.getElementById('invertAzimuth').checked = calibration.azimuth_inverted;
                document.getElementById('invertElevation').checked = calibration.elevation_inverted;
                document.getElementById('azimuthOffset').value = calibration.azimuth_offset.toFixed(2);
                document.getElementById('elevationOffset').value = calibration.elevation_offset.toFixed(2);
                
                log('Wczytano ustawienia kalibracji', 'success');
                
            } catch (error) {
                log('Błąd wczytywania kalibracji: ' + error.message, 'error');
            }
        }

        function getStepSize() {
            return parseFloat(document.getElementById('stepSizeInput').value) || 1.0;
        }

        async function singleAxisMove(axis, direction) {
            const stepSize = getStepSize();
            
            try {
                await apiCall('/move_axis', 'POST', {
                    axis: axis,
                    direction: direction,
                    amount: stepSize
                });
                
                log(`Ruch ${axis} ${direction} o ${stepSize}°`);
                
            } catch (error) {
                log(`Błąd ruchu w osi: ${error.message}`, 'error');
            }
        }

        function applyOffsets() {
            // Ta funkcja jest teraz zastąpiona przez applyAxisSettings()
            applyAxisSettings();
        }

        function toggleAdvancedOptions(button) {
            const container = document.getElementById('advancedOptionsContainer');
            const isVisible = container.style.display !== 'none';
            container.style.display = isVisible ? 'none' : 'grid';
            button.textContent = isVisible ? 'Opcje Zaawansowane ▼' : 'Opcje Zaawansowane ▲';
        }

        // Zaktualizowana funkcja inicjalizacji ustawień z pamięci lokalnej
        function loadLocalSettings() {
            const invertAzimuth = localStorage.getItem('invertAzimuth') === 'true';
            const invertElevation = localStorage.getItem('invertElevation') === 'true';
            const azimuthOffset = parseFloat(localStorage.getItem('azimuthOffset')) || 0;
            const elevationOffset = parseFloat(localStorage.getItem('elevationOffset')) || 0;

            document.getElementById('invertAzimuth').checked = invertAzimuth;
            document.getElementById('invertElevation').checked = invertElevation;
            document.getElementById('azimuthOffset').value = azimuthOffset;
            document.getElementById('elevationOffset').value = elevationOffset;
        }

        // Przywróć ustawienia przy starcie
        document.addEventListener('DOMContentLoaded', function() {
            loadLocalSettings();
            
            // Wczytaj kalibrację z serwera po połączeniu
            setTimeout(() => {
                if (isConnected) {
                    loadCalibrationSettings();
                }
            }, 2000);
        });
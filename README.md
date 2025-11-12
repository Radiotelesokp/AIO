# Oprogramowanie projektu Radioteleskop

Niniejszy projekt jest kompletnym rozwiązaniem zapewniającym obsługę radioteleskopu.

## Spis treści
1. [Architektura systemu](#architektura-systemu)
2. [REST API](#REST-API)
3. [Opis rozwiązania](#opis-rozwiązania)
4. [Dalsze ścieżki rozwoju](#dalsze-ścieżki-rozwoju)

## Architektura systemu

## REST API

## Opis rozwiązania
### Sterownik

### SDR

### Panel sterowania
Panel sterowania umożliwia podgląd oraz sterowanie radioteleskopem. Na bieżąco pokazuje co się dzieje

### HealthCheck
Jest to moduł sprawdzający poprawność działania SDR oraz Sterownika. W przypadku jakichkolwiek 
zbyt długiego czasu odpowiedzi odpowiedni serwis zostanie zresetowane.

## Dalsze ścieżki rozwoju
Poniżej znajdują się warte uwagi propozycje dalszego rozwoju naszego oprogramowania:
1. Implementacja HealthCheck.
2. Planer obserwacji - moduł umożliwiałby zaplanowanie oraz automatyzację prowadzenia obserwacji.
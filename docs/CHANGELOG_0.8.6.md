# 0.8.6 — awanse: przyrosty, kaskada, „Zamknij”

## Interfejs

Osobne podsumowanie każdego poziomu przy lewej krawędzi. Jeden przyrost na wiersz, bez kolumn ani liczb „przed / po”; brak wierszy zerowych. Oddzielne rzuty obronne, przyrosty cech i modyfikatorów, HP, mana, premie ataków, ST, biegłość, dodatkowe ataki, kręgi, obrażenia sztuczek, leczenie i dostępne ulepszenia zdolności. Nowe czary z ikonami. Shillelagh pokazuje podpisany przyrost średnich obrażeń zamiast dwóch rodzajów kości.

Kaskada samodzielnych paneli bez automatycznego znikania. Wybrany nagłówek przenosi panel na wierzch, bez trwałego zakrywania nagłówków pozostałych. Krzyżyk i dolny **Zamknij** potwierdzają tylko swój identyfikator. Długa zawartość przewija się wewnątrz, przycisk zostaje na dole. Usunięto ogólne, międzyklasowe powiadomienia o progach; zastępują je konkretne przyrosty własnej postaci.

## Serwer i zapis

`server/level_up.py` oblicza stałe przyrosty z istniejących funkcji walki. Podsumowania używają wyposażenia i mistrzostwa z chwili awansu, a nie późniejszego stanu. Historia jest prywatna. Kompaktowe stany przesyłają ją ponownie tylko po zmianie. Zapis zachowuje oczekujące podsumowania i ich indywidualne potwierdzenia; starsze zapisy nie dostają retroaktywnego zalewu paneli.

Nagroda za kilka poziomów daje po jednym podsumowaniu dla każdego. Bardzo długie serie używają zakresów. Widok materializuje 32 najnowsze niezamknięte podsumowania, pozostałe są zachowane i pojawiają się przy zwalnianiu miejsca. Licznik pokazuje cały zaległy zbiór. Zamknięcie panelu nie wydaje punktów, nie zmienia statystyk i nie wybiera zdolności.

## Przydział punktów

Punkt dotychczasowego mistrzostwa ma przycisk przejścia do Statystyk. Karta umożliwia faktyczny przydział z walidacją serwera. Dla samego przydziału zniesiono konieczność stania przy mistrzu; pozostałe warunki zachowano. Nie dodano atutów, waluty ani nowego systemu punktów cech. Przygotowane jest przekierowanie do Atutów dla przyszłych rzeczywistych wyborów.

## Klienci i wydanie

Nowe moduły `web/level_up.js`, `web/level_up.css`, `client/scripts/level_up.gd`. Zmienione karta postaci, integracja klienta, trasy HTTP, dane prywatne i obsługa zapisu. Źródła Godota bez testu w silniku lub eksportu. Metadane: 0.8.6, Android code 13. Pełne źródła; brak plików APK/AAB/EXE i kluczy podpisu.

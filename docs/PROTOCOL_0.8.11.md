# Protokół 0.8.11

Dotychczasowe komendy i zapis postaci pozostają bez zmiany. Nowe pole metadanych `welcome.world.class_progression` jest mapą `class_id -> [{level, name, description, spells}]`. `spells` to identyfikatory dokładnie tych zdolności, które ta klasa odblokowuje na danym poziomie. Informacje generuje `server/progression_guide.py` z `dnd_content` i `combat_rules`.

Przewodnik nie jest podsumowaniem indywidualnego awansu: opisuje bazowy stały rozwój danej klasy. Nie obejmuje tymczasowych statusów ani bieżących parametrów założonego sprzętu. Faktyczne przyrosty awansu nadal zapewnia istniejący `level_up`.

Mapa korzysta z istniejącego `world.river` oraz `waterways`/`bridges`; nie zmieniono geometrii ani kolizji świata. `web/atlas_map.js` jest dodatkową trasą statyczną obsługiwaną przez serwer. Kamera atlasu jest stanem klienta w bieżącej sesji i nie zmienia bazy.

Klient nie resetuje już wektora ruchu przy komendach `select_target`, otwieraniu zwykłych okien i ich przeciąganiu. Ochrona inputu podczas wpisywania czatu, ukrycia aplikacji i śmierci pozostaje. Cel ataku i wektor ruchu nadal weryfikuje serwer; nie dodano autorytetu klientowi nad obrażeniami, teleportacją ani PvP.

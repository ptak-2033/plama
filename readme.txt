# PLAMA

PLAMA to **system wizualny oparty na plikach**, w którym foldery i procesy są traktowane jak **obiekty na mapie**.

Główny skrypt `plama.py` **nie zawiera logiki obiektów** – jest tylko **ekranem / mapą**, która odczytuje aktualny stan systemu z folderów.

---

## Jak to działa

### Obiekty
- Każdy obiekt to **folder w katalogu `obiekty/`**
- W folderze obiektu znajduje się plik `mapa_dane.txt`
- Na podstawie `mapa_dane.txt` mapa wie:
  - jak obiekt wygląda
  - jaki ma rozmiar
  - gdzie jest położony
  - jaki ma status (on / off / error)

Mapa **niczego nie wymusza** — tylko **odczytuje stan plików**.

---

### Linie (połączenia)
- Każde połączenie między obiektami to **osobny folder w katalogu `linie/`**
- Linia reprezentuje zależność / kolejność uruchamiania
- Dodanie lub usunięcie folderu linii **natychmiast zmienia mapę**

---

### Uruchamianie
- Gdy obiekt zostaje uruchomiony:
  - jego wyjście może zostać przekazane jako wejście do kolejnego obiektu  
  **lub**
  - może po prostu **uruchomić następny obiekt bez przekazywania danych**

Logika wykonania **żyje w obiektach**, nie w mapie.

---

## Filozofia

- Wszystko istnieje **fizycznie na dysku**
- Brak baz danych, chmury i ukrytego stanu
- Foldery są prawdą
- Mapa jest tylko wizualizacją

PLAMA to bardziej **język systemowy oparty na plikach** niż klasyczna aplikacja.

---

## Status

Projekt jest we wczesnym etapie (**alpha**).  
Struktura jest stabilna, logika będzie dalej rozwijana.

---

## License

MIT License  
© 2025 ptak-2033

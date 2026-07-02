"""Test del filtro en vivo del selector de paises."""

from tacticore.ui.screens.country_select_screen import CountrySelectScreen

_COUNTRIES = [("Argentina", "AR"), ("Brasil", "BR"), ("Alemania", "DE"),
              ("Italia", "IT")]


def test_visible_is_sorted_and_filters_by_name():
    screen = CountrySelectScreen(list(_COUNTRIES))
    # Sin filtro: todos, ordenados por nombre.
    assert [c[0] for c in screen._visible()] == \
        ["Alemania", "Argentina", "Brasil", "Italia"]
    # Filtro por substring (case-insensitive).
    screen._query = "ar"
    assert [c[0] for c in screen._visible()] == ["Argentina"]
    screen._query = "A"
    assert len(screen._visible()) == 4  # todos tienen una 'a'
    screen._query = "zzz"
    assert screen._visible() == []

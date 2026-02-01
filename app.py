<style>
  /* Usuwamy marginesy bloga dla tego elementu */
  .full-width-casino {
    width: 100%;
    max-width: 100%;
    margin: 0 auto;
    background-color: #000000; /* Czarne tło dla Kasyna */
    overflow: hidden;
    position: relative;
    border: 1px solid #333333; /* Ciemna ramka */
    border-radius: 12px;
    /* Wysokość dostosowana do urządzeń mobilnych */
    height: 85vh; 
    box-shadow: 0 4px 15px rgba(0,0,0,0.5);
  }

  /* Styl samej ramki */
  .full-width-casino iframe {
    width: 100%;
    height: 100%;
    border: none;
    display: block;
  }

  /* Poprawka dla bardzo małych ekranów */
  @media only screen and (max-width: 480px) {
    .full-width-casino {
      height: 75vh;
      border-radius: 0;
      border: none;
    }
  }
</style>

<div class="full-width-casino">
  <iframe 
    src="https://gencasino.streamlit.app/?embed=true" 
    title="Casino Lotto Generator"
    allow="clipboard-read; clipboard-write;"
    allowfullscreen
    loading="lazy">
  </iframe>
</div>

<p style="text-align: center; font-family: sans-serif; font-size: 12px; color: #888; margin-top: 10px;">
  Maszyna nie działa? 
  <a href="https://gencasino.streamlit.app/" target="_blank" style="color: #FF0055; text-decoration: none; font-weight: bold;">
    🎰 Otwórz Kasyno w nowym oknie
  </a>
</p>

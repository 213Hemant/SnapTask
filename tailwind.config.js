/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
     // 1. All HTML files within your 'templates' directory and any subdirectories
    "./templates/**/*.html",
    
    // 2. Any JavaScript files where you might be dynamically adding Tailwind classes
    //    Based on your image, this would be your 'main.js' and any other JS files in 'static'
    "./static/**/*.js", 

    // You might also include your app.py if you construct Tailwind class strings there,
    // though it's less common.
    // "./app.py", 
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}


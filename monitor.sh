while [ true ] ; do
  ./fix_books.py
  sed -i '$s/,$//' maker-matcher.json
  #sed -i '$s/"}{"/"},{"/' maker-matcher.json
  scp maker-matcher.json reidy@riverhead.org:www/.
  sleep 5
done

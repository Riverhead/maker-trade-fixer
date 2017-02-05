while [ true ] ; do
  ./fix_books.py
  sed -i '$s/,$//' maker-matcher.json
  #sed -i '$s/"}{"/"},{"/' maker-matcher.json
  sleep 5
done

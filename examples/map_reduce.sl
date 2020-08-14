(let f ["x" "x" "x" "x" "a" "b" "c" "d" "e" "a" "b" "c"]);
(func map f:
  (if f
    (let h (head f));
    (let t (tail f));
    (push [h 1] (call map t))
    []
  )
);
(func in m k:
  (func helper l:
    (if l
      (let h (head l));
      (let t (tail l));
      (if (== h k)
        True
        (call helper t)
      )
      False
    )
  );
  (let ks (keys m));
  (call helper ks)
);
(func reduce l:
  (if l
    (let t (tail l));
    (let m (call reduce t));
    (let e (head l));
    (let k (head e));
    (let v (head (tail e)));
    (let currv (if (call in m k)
      (get m k)
      0
    ));
    (put m k (+ currv v))
    {}
  )
);
(let l (call map f));
(let o (call reduce l))
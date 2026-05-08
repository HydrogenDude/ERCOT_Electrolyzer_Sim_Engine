function y = safe_divide(a,b)
y = zeros(size(a));
mask = b > 0;
y(mask) = a(mask) ./ b(mask);
end
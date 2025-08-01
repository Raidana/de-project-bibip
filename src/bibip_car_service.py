import os
from datetime import datetime
from decimal import Decimal
from typing import Optional
from models import Car, CarStatus, CarFullInfo, Model, Sale, ModelSaleStats


class CarService:
    def __init__(self, root_directory_path: str):
        self.root_directory_path = root_directory_path

    def _get_index(self, index_file: str) -> list[tuple[str, int]]:
        if not os.path.exists(index_file):
            return []

        with open(index_file, "r", encoding="utf-8") as f:
            return [line.strip().split(" ", 1) for line in f.readlines()]

    def _write_fixed(self, file_path: str, line_number: int, content: str, line_length: int = 501):
        with open(file_path, "r+", encoding="utf-8") as f:
            f.seek(line_number * line_length)
            f.write(content.ljust(line_length - 1) + "\n")

    def add_model(self, model: Model) -> None:
        models_file = os.path.join(self.root_directory_path, "models.txt")
        models_index_file = os.path.join(self.root_directory_path, "models_index.txt")

        with open(models_file, "a", encoding="utf-8") as f:
            offset = f.tell()
            f.write(model.model_dump_json().ljust(500) + "\n")

        with open(models_index_file, "a", encoding="utf-8") as f:
            f.write(f"{model.id} {offset}\n")

    def add_car(self, car: Car) -> None:
        cars_file = os.path.join(self.root_directory_path, "cars.txt")
        cars_index_file = os.path.join(self.root_directory_path, "cars_index.txt")

        with open(cars_file, "a", encoding="utf-8") as f:
            offset = f.tell()
            f.write(car.model_dump_json().ljust(500) + "\n")

        with open(cars_index_file, "a", encoding="utf-8") as f:
            f.write(f"{car.vin} {offset}\n")

    def sell_car(self, sale: Sale) -> Car:
        sales_file = os.path.join(self.root_directory_path, "sales.txt")
        sales_index_file = os.path.join(self.root_directory_path, "sales_index.txt")

        with open(sales_file, "a", encoding="utf-8") as f:
            offset = f.tell()
            f.write(sale.model_dump_json().ljust(500) + "\n")

        with open(sales_index_file, "a", encoding="utf-8") as f:
            f.write(f"{sale.sales_number} {offset}\n")

        cars_index_file = os.path.join(self.root_directory_path, "cars_index.txt")
        cars_file = os.path.join(self.root_directory_path, "cars.txt")

        car_index = self._get_index(cars_index_file)
        offset = next((int(o) for v, o in car_index if v == sale.car_vin), None)
        if offset is None:
            raise ValueError("VIN not found")

        with open(cars_file, "r+", encoding="utf-8") as f:
            f.seek(offset)
            old_line = f.read(501)
            car = Car.model_validate_json(old_line.strip())
            car.status = CarStatus.sold
            f.seek(offset)
            f.write(car.model_dump_json().ljust(500) + "\n")

        return car

    def get_cars(self, status: Optional[CarStatus] = None) -> list[Car]:
        cars_file = os.path.join(self.root_directory_path, "cars.txt")
        cars = []

        with open(cars_file, "r", encoding="utf-8") as f:
            for line in f:
                car = Car.model_validate_json(line.strip())
                if status is None or car.status == status:
                    cars.append(car)
        return cars

    def get_car_info(self, vin: str) -> Optional[CarFullInfo]:
        cars_index_file = os.path.join(self.root_directory_path, "cars_index.txt")
        cars_file = os.path.join(self.root_directory_path, "cars.txt")
        models_index_file = os.path.join(self.root_directory_path, "models_index.txt")
        models_file = os.path.join(self.root_directory_path, "models.txt")
        sales_index_file = os.path.join(self.root_directory_path, "sales_index.txt")
        sales_file = os.path.join(self.root_directory_path, "sales.txt")

        car_index = self._get_index(cars_index_file)
        offset = next((int(o) for v, o in car_index if v == vin), None)
        if offset is None:
            return None

        with open(cars_file, "r", encoding="utf-8") as f:
            f.seek(offset)
            car = Car.model_validate_json(f.readline().strip())

        model_index = self._get_index(models_index_file)
        model_offset = next((int(o) for v, o in model_index if int(v) == car.model), None)
        if model_offset is None:
            return None

        with open(models_file, "r", encoding="utf-8") as f:
            f.seek(model_offset)
            model = Model.model_validate_json(f.readline().strip())

        sale_index = self._get_index(sales_index_file)
        sale_offset = next((int(o) for v, o in sale_index if vin in v), None)
        if sale_offset is not None:
            with open(sales_file, "r", encoding="utf-8") as f:
                f.seek(sale_offset)
                line = f.readline().strip()
                if line:
                    sale = Sale.model_validate_json(line)
                    return CarFullInfo(
                        vin=car.vin,
                        car_model_name=model.name,
                        car_model_brand=model.brand,
                        price=car.price,
                        date_start=car.date_start,
                        status=car.status,
                        sales_date=sale.sales_date,
                        sales_cost=sale.cost
                    )
        return CarFullInfo(
            vin=car.vin,
            car_model_name=model.name,
            car_model_brand=model.brand,
            price=car.price,
            date_start=car.date_start,
            status=car.status,
            sales_date=None,
            sales_cost=None
        )

    def update_vin(self, vin: str, new_vin: str) -> Car:
        cars_index_file = os.path.join(self.root_directory_path, "cars_index.txt")
        cars_file = os.path.join(self.root_directory_path, "cars.txt")

        car_index = self._get_index(cars_index_file)
        index_list = [(v, int(o)) for v, o in car_index]
        old_entry = next(((i, v, o) for i, (v, o) in enumerate(index_list) if v == vin), None)
        if not old_entry:
            raise ValueError("VIN not found")

        idx, old_vin, offset = old_entry

        with open(cars_file, "r+", encoding="utf-8") as f:
            f.seek(offset)
            car = Car.model_validate_json(f.read(501).strip())
            car.vin = new_vin
            f.seek(offset)
            f.write(car.model_dump_json().ljust(500) + "\n")

        index_list[idx] = (new_vin, offset)
        index_list.sort(key=lambda x: x[0])

        with open(cars_index_file, "w", encoding="utf-8") as f:
            for vin, o in index_list:
                f.write(f"{vin} {o}\n")

        return car

    def revert_sale(self, sales_number: str) -> Car:
        sales_index_file = os.path.join(self.root_directory_path, "sales_index.txt")
        sales_file = os.path.join(self.root_directory_path, "sales.txt")
        cars_index_file = os.path.join(self.root_directory_path, "cars_index.txt")
        cars_file = os.path.join(self.root_directory_path, "cars.txt")

        index = self._get_index(sales_index_file)
        sales_data = [(v, int(o)) for v, o in index if v == sales_number]
        if not sales_data:
            raise ValueError("Sale not found")

        _, offset = sales_data[0]
        with open(sales_file, "r+", encoding="utf-8") as f:
            f.seek(offset)
            sale = Sale.model_validate_json(f.read(501).strip())
            f.seek(offset)
            f.write("".ljust(500) + "\n")

        car_index = self._get_index(cars_index_file)
        car_offset = next((int(o) for v, o in car_index if v == sale.car_vin), None)
        if car_offset is None:
            raise ValueError("Car not found")

        with open(cars_file, "r+", encoding="utf-8") as f:
            f.seek(car_offset)
            car = Car.model_validate_json(f.read(501).strip())
            car.status = CarStatus.available
            f.seek(car_offset)
            f.write(car.model_dump_json().ljust(500) + "\n")

        return car

    def top_models_by_sales(self) -> list[ModelSaleStats]:
        sales_file = os.path.join(self.root_directory_path, "sales.txt")
        cars_file = os.path.join(self.root_directory_path, "cars.txt")
        cars_index_file = os.path.join(self.root_directory_path, "cars_index.txt")
        models_file = os.path.join(self.root_directory_path, "models.txt")
        models_index_file = os.path.join(self.root_directory_path, "models_index.txt")

        car_model_map = {}
        car_index = self._get_index(cars_index_file)
        with open(cars_file, "r", encoding="utf-8") as f:
            for v, o in car_index:
                f.seek(int(o))
                line = f.read(501).strip()
                if line:
                    car = Car.model_validate_json(line)
                    car_model_map[car.vin] = car.model

        sales_counter = {}
        with open(sales_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    sale = Sale.model_validate_json(line.strip())
                    model_id = car_model_map.get(sale.car_vin)
                    if model_id is not None:
                        sales_counter[model_id] = sales_counter.get(model_id, 0) + 1

        top_ids = sorted(sales_counter.items(), key=lambda x: (-x[1], -x[0]))[:3]

        index = self._get_index(models_index_file)
        id_to_offset = {int(v): int(o) for v, o in index}

        result = []
        with open(models_file, "r", encoding="utf-8") as f:
            for model_id, count in top_ids:
                offset = id_to_offset.get(model_id)
                if offset is not None:
                    f.seek(offset)
                    model = Model.model_validate_json(f.readline().strip())
                    result.append(ModelSaleStats(
                        car_model_name=model.name,
                        brand=model.brand,
                        sales_number=count
                    ))
        return result



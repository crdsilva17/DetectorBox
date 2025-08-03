import cv2
import numpy as np
from ultralytics import YOLO
import torch
from pathlib import Path

class BottleDetector:
    def __init__(self, model_path='yolo11n.pt', custom_model_path='best.pt'):
        """
        Detector aprimorado para garrafas de vidro vista de cima
        
        Args:
            model_path: Modelo YOLO padrão
            custom_model_path: Modelo customizado treinado (opcional)
        """
        # Usar modelo customizado se disponível, senão usar o padrão
        if custom_model_path and Path(custom_model_path).exists():
            self.model = YOLO(custom_model_path)
            self.is_custom = True
        else:
            self.model = YOLO(model_path)
            self.is_custom = False
        
        # Configurações para vista de cima
        self.confidence_threshold = 0.3  # Menor para capturar mais detecções
        self.nms_threshold = 0.4  # Non-maximum suppression
        
    def preprocess_top_view_image(self, image):
        """
        Pré-processamento específico para vista de cima
        """
        # Realçar contraste
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
        
        return enhanced
    
    def detect_circular_shapes(self, image,minDist=90, param1=50, param2=45, min_radius=45, max_radius=60):
        """
        Detectar formas circulares (tampas de garrafa) usando Hough Circles
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.medianBlur(gray, 5)
        
        circles = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=minDist,
            param1=param1,
            param2=param2,
            minRadius=min_radius,
            maxRadius=max_radius
        )
        
        circle_detections = []
        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            for (x, y, r) in circles:
                # Criar bounding box a partir do círculo
                x1 = max(0, x - r)
                y1 = max(0, y - r)
                x2 = min(image.shape[1], x + r)
                y2 = min(image.shape[0], y + r)
                
                circle_detections.append({
                    'bbox': [x1, y1, x2, y2],
                    'center': (x, y),
                    'radius': r,
                    'confidence': 0.8,  # Confiança baseada na detecção circular
                    'method': 'hough_circles'
                })
        
        return circle_detections
    
    def detect_with_yolo(self, image):
        """Detecção usando YOLO"""
        results = self.model(image, conf=self.confidence_threshold)
        
        detections = []
        if results[0].boxes is not None:
            for box in results[0].boxes:
                if self.is_custom or int(box.cls) == 39:  # 39 = bottle no COCO
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    confidence = float(box.conf[0])
                    
                    detections.append({
                        'bbox': [int(x1), int(y1), int(x2), int(y2)],
                        'confidence': confidence,
                        'method': 'yolo'
                    })
        
        return detections
    
    def merge_detections(self, yolo_detections, circle_detections, iou_threshold=0.3):
        """
        Combinar detecções do YOLO e Hough Circles
        """
        all_detections = []
        
        # Adicionar detecções YOLO
        for det in yolo_detections:
            det['source'] = 'yolo'
            all_detections.append(det)
        
        # Adicionar detecções circulares que não se sobrepõem muito com YOLO
        for circle_det in circle_detections:
            overlap = False
            for yolo_det in yolo_detections:
                if self.calculate_iou(circle_det['bbox'], yolo_det['bbox']) > iou_threshold:
                    overlap = True
                    break
            
            if not overlap:
                circle_det['source'] = 'hough'
                all_detections.append(circle_det)
        
        return all_detections
    
    def calculate_iou(self, box1, box2):
        """Calcular Intersection over Union (IoU)"""
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2
        
        # Coordenadas da interseção
        x1_inter = max(x1_1, x1_2)
        y1_inter = max(y1_1, y1_2)
        x2_inter = min(x2_1, x2_2)
        y2_inter = min(y2_1, y2_2)
        
        if x2_inter <= x1_inter or y2_inter <= y1_inter:
            return 0.0
        
        # Área da interseção
        inter_area = (x2_inter - x1_inter) * (y2_inter - y1_inter)
        
        # Áreas das caixas
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        
        # União
        union_area = area1 + area2 - inter_area
        
        return inter_area / union_area if union_area > 0 else 0.0
    
    def detect_bottles_in_box_enhanced(self, image_input, box_roi=None, 
                                     use_preprocessing=True, use_hough=True,
                                     minDist=90, param1=50, param2=45, min_radius=45, max_radius=60):
        """
        Detecção aprimorada combinando múltiplas técnicas
        """
        if isinstance(image_input, str) or isinstance(image_input, Path):
            # É um path - carregar imagem
            image = cv2.imread(str(image_input))
            if image is None:
                raise ValueError(f"Não foi possível carregar a imagem: {image_input}")
        elif isinstance(image_input, np.ndarray):
            # É uma imagem já carregada
            image = image_input.copy()
        else:
            raise ValueError("image_input deve ser um path (str) ou uma imagem (numpy.ndarray)")
        
        original_image = image.copy()
        
        # Aplicar ROI se especificada
        if box_roi:
            x1, y1, x2, y2 = box_roi
            image = image[y1:y1+y2, x1:x1+x2]
        
        # Pré-processamento
        if use_preprocessing:
            processed_image = self.preprocess_top_view_image(image)
        else:
            processed_image = image
        
        # Detecção YOLO
        yolo_detections = self.detect_with_yolo(processed_image)
        
        # Detecção de círculos
        circle_detections = []
        if use_hough:
            circle_detections = self.detect_circular_shapes(image, minDist, param1, param2, min_radius, max_radius)
        
        # Combinar detecções
        combined_detections = self.merge_detections(yolo_detections, circle_detections)
        
        # Ajustar coordenadas se ROI foi usada
        if box_roi:
            for det in combined_detections:
                det['bbox'][0] += box_roi[0]  # x1
                det['bbox'][1] += box_roi[1]  # y1
                det['bbox'][2] += box_roi[0]  # x2
                det['bbox'][3] += box_roi[1]  # y2
        
        # Anotar imagem
        annotated_image = self.annotate_enhanced(original_image, combined_detections, box_roi)
        
        return combined_detections, annotated_image
    
    def annotate_enhanced(self, image, detections, box_roi=None):
        """Anotação aprimorada com diferentes cores por método"""
        annotated = image.copy()
        
        # Desenhar ROI
        if box_roi:
            x1, y1, x2, y2 = box_roi
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 255), 2)
            cv2.putText(annotated, 'Box ROI', (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Cores por método
        colors = {
            'yolo': (0, 255, 0),    # Verde
            'hough': (255, 0, 0),   # Azul
            'combined': (0, 0, 255)  # Vermelho
        }
        
        for i, det in enumerate(detections):
            x1, y1, x2, y2 = det['bbox']
            confidence = det['confidence']
            source = det.get('source', 'unknown')
            
            color = colors.get(source, (255, 255, 255))
            
            # Retângulo
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            # Label
            label = f"Bottle {i+1} ({source}): {confidence:.2f}"
            cv2.putText(annotated, label, (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            
            # Desenhar centro se for detecção circular
            if 'center' in det:
                center = det['center']
                cv2.circle(annotated, center, 3, color, -1)
        
        # Estatísticas
        yolo_count = sum(1 for d in detections if d.get('source') == 'yolo')
        hough_count = sum(1 for d in detections if d.get('source') == 'hough')
        
        cv2.putText(annotated, f"Total: {len(detections)}", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(annotated, f"YOLO: {yolo_count}, Hough: {hough_count}", 
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        return annotated

# Exemplo de uso
def main():
    # Inicializar detector aprimorado
    detector = BottleDetector()
    
    # Configurar para sua imagem
    image_path = "resource/20250729_000733.jpg"
    # if image_path is None:
    #     return
    # image = cv2.imread(image_path)
    last_frame = cv2.imread(image_path)
    if last_frame is None:
        raise ValueError(f"Could not read image file {image_path}.")
        # Redimensiona a imagem para o tamanho máximo permitido
    frame = cv2.resize(last_frame, (640, 480))
    image = frame.copy()

    # frame = cv2.resize(image, dsize=(640, 480), interpolation=cv2.INTER_LINEAR)
    last = image.copy()
    
    # ROI da caixa (ajustar conforme necessário)
    box_roi = [350, 1200, 1800, 3200]  # [x1, y1, x2, y2]
    
    try:
        # Detecção aprimorada
        detections, annotated_image = detector.detect_bottles_in_box_enhanced(
            last, 
            box_roi=box_roi,
            use_preprocessing=True,
            use_hough=True
        )
        
        print(f"Total de garrafas detectadas: {len(detections)}")
        
        # Detalhes das detecções
        for i, det in enumerate(detections):
            source = det.get('source', 'unknown')
            conf = det['confidence']
            print(f"Garrafa {i+1}: {source} (confiança: {conf:.2f})")
        
        # Salvar resultado
        cv2.imwrite("deteccao_aprimorada.jpg", annotated_image)
        print("Resultado salvo em 'deteccao_aprimorada.jpg'")
        
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    main()
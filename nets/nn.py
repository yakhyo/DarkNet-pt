import torch
import torch.nn as nn
from torch.nn import MaxPool2d
from utils import GlobalAvgPool2d, auto_pad


class Conv(nn.Module):
    def __init__(self, c1, c2, k=1, s=1, p=None, g=1, act=True):
        super(Conv, self).__init__()
        self.conv = nn.Conv2d(c1, c2, k, s, auto_pad(k, p), groups=g, bias=False)
        self.bn = nn.BatchNorm2d(c2)
        self.act = nn.LeakyReLU() if act else nn.ReLU()

    def forward(self, x):
        return self.act(self.bn(self.conv(x)))


class ResidualBlock(nn.Module):
    def __init__(self, c1):
        super(ResidualBlock, self).__init__()
        c2 = c1 // 2
        self.layer1 = Conv(c1, c2, p=0)
        self.layer2 = Conv(c2, c1, k=3)

    def forward(self, x):
        residual = x
        out = self.layer1(x)
        out = self.layer2(out)
        out += residual
        return out


class DarkNet19(nn.Module):
    def __init__(self, num_classes=1000, init_weight=True):
        super(DarkNet19, self).__init__()

        if init_weight:
            self._initialize_weights()

        self.features = nn.Sequential(
            Conv(3, 32, 3),
            MaxPool2d(2, 2),

            Conv(32, 64, 3),
            MaxPool2d(2, 2),

            Conv(64, 128, 3),
            Conv(128, 64, 1),
            Conv(64, 128, 3),
            MaxPool2d(2, 2),

            Conv(128, 256, 3),
            Conv(256, 128, 1),
            Conv(128, 256, 3),
            MaxPool2d(2, 2),

            Conv(256, 512, 3),
            Conv(512, 256, 1),
            Conv(256, 512, 3),
            Conv(512, 256, 1),
            Conv(256, 512, 3),
            MaxPool2d(2, 2),

            Conv(512, 1024, 3),
            Conv(1024, 512, 1),
            Conv(512, 1024, 3),
            Conv(1024, 512, 1),
            Conv(512, 1024, 3),
        )

        self.classifier = nn.Sequential(
            *self.features,
            Conv(1024, num_classes, 1),
            GlobalAvgPool2d(),
            nn.Softmax(dim=1)
        )

    def forward(self, x):
        return self.classifier(x)

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_in', nonlinearity='leaky_relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.01)
                nn.init.constant_(m.bias, 0)


class DarkNet53(nn.Module):
    def __init__(self, block, num_classes=1000, init_weight=True):
        super(DarkNet53, self).__init__()
        self.num_classes = num_classes

        if init_weight:
            self._initialize_weights()

        self.features = nn.Sequential(
            Conv(3, 32, 3),
            Conv(32, 64, 3, 2),

            *self._make_layer(block, 64, num_blocks=1),
            Conv(64, 128, 3, 2),

            *self._make_layer(block, 128, num_blocks=2),
            Conv(128, 256, 3, 2),

            *self._make_layer(block, 256, num_blocks=8),
            Conv(256, 512, 3, 2),

            *self._make_layer(block, 512, num_blocks=8),
            Conv(512, 1024, 3, 2),

            *self._make_layer(block, 1024, num_blocks=4)
        )
        self.classifier = nn.Sequential(
            *self.features,
            GlobalAvgPool2d(),
            nn.Linear(1024, num_classes),
            nn.Softmax(dim=1)
        )

    def forward(self, x):
        return self.classifier(x)

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_in', nonlinearity='leaky_relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.01)
                nn.init.constant_(m.bias, 0)

    @staticmethod
    def _make_layer(block, in_channels, num_blocks):
        layers = []
        for i in range(0, num_blocks):
            layers.append(block(in_channels))
        return nn.Sequential(*layers)


def darknet53(num_classes=1000, init_weight=True):
    return DarkNet53(ResidualBlock, num_classes=num_classes, init_weight=init_weight)


def darknet19(num_classes=1000, init_weight=True):
    return DarkNet19(num_classes=num_classes, init_weight=init_weight)


if __name__ == '__main__':
    darknet19 = DarkNet19(num_classes=1000, init_weight=True)
    darknet19_features = darknet19.features

    darknet53 = DarkNet53(ResidualBlock, num_classes=1000, init_weight=True)
    darknet53_features = darknet53.features

    print('Num. of Params of DarkNet: {}'.format(sum(p.numel() for p in darknet19.parameters() if p.requires_grad)))
    print('Num. of Params of DarkNet53: {}'.format(sum(p.numel() for p in darknet53.parameters() if p.requires_grad)))

    x = torch.randn(1, 3, 256, 256)

    print('Output of DarkNet: {}'.format(darknet19(x).shape))
    print('Output of DarkNet53: {}'.format(darknet53(x).shape))

    print('Feature Extractor Output of DarkNet: {}'.format(darknet19_features(x).shape))
    print('Feature Extractor Output of DarkNet53: {}'.format(darknet53_features(x).shape))